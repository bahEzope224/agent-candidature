from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_offer import JobOffer, Company
from app.models.application import Application
from app.services.scraper.base import RawJobOffer
import structlog
import uuid as uuid_lib

logger = structlog.get_logger()


async def get_or_create_company(db: AsyncSession, name: str) -> Company:
    result = await db.execute(select(Company).where(Company.name == name))
    company = result.scalar_one_or_none()
    if not company:
        company = Company(name=name)
        db.add(company)
        await db.flush()
    return company


async def save_job_offer(
    db: AsyncSession,
    raw: RawJobOffer,
    user_id: uuid_lib.UUID,
) -> tuple[JobOffer, bool]:
    """
    Sauvegarde une offre liée à un utilisateur.
    Le hash est maintenant user_id + url pour permettre
    à plusieurs users de scrapper la même offre.
    """
    offer_hash = f"{str(user_id)}:{raw.compute_hash()}"

    result = await db.execute(
        select(JobOffer).where(JobOffer.hash == offer_hash)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False

    company = await get_or_create_company(db, raw.company_name)
    offer = JobOffer(
        user_id=user_id,
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
    logger.info("Offre sauvegardée", title=raw.title, company=raw.company_name, user=str(user_id))
    return offer, True


async def save_many_offers(
    db: AsyncSession,
    raw_offers: list[RawJobOffer],
    user_id: uuid_lib.UUID,
) -> dict:
    """Sauvegarde une liste d'offres pour un utilisateur donné"""
    created = 0
    skipped = 0
    for raw in raw_offers:
        _, is_new = await save_job_offer(db, raw, user_id)
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
    application = Application(
        user_id=user_id,
        job_offer_id=offer.id,
        email_subject=generated.get("email_subject"),
        email_body=generated.get("email_body"),
        cover_letter_text=generated.get("cover_letter"),
        llm_confidence_score=confidence,
        requires_human_validation=confidence < 0.85,
        status="to_apply",
    )
    db.add(application)
    await db.flush()
    logger.info("Candidature créée", offer=offer.title, confidence=confidence)
    return application