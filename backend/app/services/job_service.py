from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_offer import JobOffer, Company
from app.models.application import Application
from app.services.scraper.base import RawJobOffer
import structlog
import uuid as uuid_lib

logger = structlog.get_logger()


async def get_or_create_company(
    db: AsyncSession,
    name: str,
) -> Company:
    """Récupère ou crée une entreprise"""
    result = await db.execute(
        select(Company).where(Company.name == name)
    )
    company = result.scalar_one_or_none()

    if not company:
        company = Company(name=name)
        db.add(company)
        await db.flush()

    return company


async def save_job_offer(
    db: AsyncSession,
    raw: RawJobOffer,
) -> tuple[JobOffer, bool]:
    """
    Sauvegarde une offre en BDD.
    Retourne (offer, created) — created=False si déjà existante.
    """
    offer_hash = raw.compute_hash()

    result = await db.execute(
        select(JobOffer).where(JobOffer.hash == offer_hash)
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing, False

    company = await get_or_create_company(db, raw.company_name)

    offer = JobOffer(
        company_id=company.id,
        title=raw.title,
        description=raw.description,
        location=raw.location,
        contract_type=raw.contract_type,
        duration_months=raw.duration_months,
        source_platform=raw.source_platform,
        source_url=raw.source_url,
        hash=offer_hash,
        posted_at=raw.posted_at,
        status="to_review",
    )
    db.add(offer)
    await db.flush()

    logger.info("Offre sauvegardée", title=raw.title, company=raw.company_name)
    return offer, True


async def save_many_offers(
    db: AsyncSession,
    raw_offers: list[RawJobOffer],
) -> dict:
    """Sauvegarde une liste d'offres, retourne les stats"""
    created = 0
    skipped = 0

    for raw in raw_offers:
        _, is_new = await save_job_offer(db, raw)
        if is_new:
            created += 1
        else:
            skipped += 1

    await db.commit()
    return {"created": created, "skipped": skipped, "total": len(raw_offers)}


async def create_application_draft(
    db: AsyncSession,
    offer: JobOffer,
    generated: dict,
    user_id: uuid_lib.UUID,
) -> Application:
    """Crée une candidature en brouillon en base"""
    confidence = generated.get("confidence_score", 0.0)
    requires_validation = confidence < 0.85

    application = Application(
        user_id=user_id,
        job_offer_id=offer.id,
        email_subject=generated.get("email_subject"),
        email_body=generated.get("email_body"),
        cover_letter_text=generated.get("cover_letter"),
        llm_confidence_score=confidence,
        requires_human_validation=requires_validation,
        status="pending_review" if requires_validation else "ready_to_send",
    )

    db.add(application)
    await db.flush()

    logger.info(
        "Candidature créée",
        offer=offer.title,
        status=application.status,
        confidence=confidence,
    )
    return application