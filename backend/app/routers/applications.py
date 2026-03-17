"""
Router Applications — MODE MANUEL
----------------------------------
L'envoi automatique de mails et la candidature automatique sont
temporairement désactivés. L'utilisateur candidate et relance manuellement.

Flux :
  to_apply → [utilisateur confirme] → sent
  sent + J+7 → follow_up_needed (+ mail de relance généré)
  follow_up_needed → [utilisateur confirme] → follow_up_sent
  follow_up_sent + J+7 → no_response
  sent / follow_up_sent → interview | refused  (mise à jour manuelle)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from app.database import get_db
from app.models.job_offer import JobOffer
from app.models.application import Application
from app.models.user import User
from app.services.generator import generate_application, profile_to_candidate
from app.models.profile import Profile
from app.services.job_service import create_application_draft
from app.services.auth_service import get_current_user
import uuid

router = APIRouter()


# ================================================================
# ROUTES STATIQUES — doivent être AVANT /{application_id}
# ================================================================

@router.get("/")
async def list_applications(
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retourne le dashboard de l'utilisateur connecté uniquement.
    Inclut le lien de l'offre et le mail généré pour candidature manuelle.
    """
    query = (
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .where(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
    )
    if status:
        query = query.where(Application.status == status)
    result = await db.execute(query)
    apps = result.scalars().all()
    now = datetime.utcnow()
    return [
        {
            "id": str(a.id),
            "offer": a.job_offer.title if a.job_offer else "N/A",
            "company": a.job_offer.company.name if a.job_offer and a.job_offer.company else "N/A",
            "score": a.job_offer.relevance_score if a.job_offer else None,
            # Lien direct vers l'offre pour candidater manuellement
            "offer_url": a.job_offer.source_url if a.job_offer else None,
            "status": a.status,
            "confidence": a.llm_confidence_score,
            "email_subject": a.email_subject,
            # Indique depuis combien de jours la candidature est dans ce statut
            "days_in_status": (now - a.sent_at).days if a.sent_at else None,
            "sent_at": str(a.sent_at) if a.sent_at else None,
            "followup_sent_at": str(a.followup_sent_at) if a.followup_sent_at else None,
            "created_at": str(a.created_at),
        }
        for a in apps
    ]


@router.get("/pending-followups")
async def pending_followups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste les candidatures de l'utilisateur connecté dont le statut est 'follow_up_needed'.
    """
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .where(
            Application.status == "follow_up_needed",
            Application.user_id == current_user.id,
        )
    )
    apps = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "offer": a.job_offer.title if a.job_offer else "N/A",
            "company": a.job_offer.company.name if a.job_offer and a.job_offer.company else "N/A",
            "offer_url": a.job_offer.source_url if a.job_offer else None,
            "sent_at": str(a.sent_at),
            "days_since_sent": (datetime.utcnow() - a.sent_at).days if a.sent_at else 0,
            # Mail de relance prêt à copier-coller
            "followup_email_body": a.followup_email_body,
            "followup_email_subject": f"Re : {a.email_subject}" if a.email_subject else "Relance candidature",
        }
        for a in apps
    ]


@router.post("/generate-batch")
async def generate_batch(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Génère des lettres de motivation pour les offres shortlistées.
    Les candidatures sont liées à l'utilisateur connecté.
    """
    result = await db.execute(
        select(JobOffer)
        .options(selectinload(JobOffer.company))
        .where(JobOffer.status == "shortlisted")
        .order_by(JobOffer.relevance_score.desc())
        .limit(limit)
    )
    offers = result.scalars().all()
    if not offers:
        return {"message": "Aucune offre shortlistée à traiter", "generated": 0}

    results = []
    for offer in offers:
        try:
            # Récupère le profil
            profile_res = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
            profile = profile_res.scalar_one_or_none()
            candidate = profile_to_candidate(profile) if profile else None

            generated = await generate_application(offer, candidate)
            application = await create_application_draft(db, offer, generated, current_user.id)
            application.status = "to_apply"
            results.append({
                "application_id": str(application.id),
                "offer": offer.title,
                "company": offer.company.name if offer.company else "Inconnue",
                "score": offer.relevance_score,
                "offer_url": offer.source_url,
                "email_subject": generated.get("email_subject"),
                "email_body": generated.get("email_body"),
                "cover_letter": generated.get("cover_letter"),
                "confidence": generated.get("confidence_score"),
                "status": "to_apply",
                "action_required": "Candidatez manuellement via le lien, puis confirmez avec PATCH /{id}/confirm-sent",
            })
        except Exception as e:
            results.append({"offer": offer.title, "error": str(e)})
    await db.commit()
    return {"generated": len(results), "results": results}


@router.post("/check-followup-deadlines")
async def check_followup_deadlines(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Vérifie les délais pour l'utilisateur connecté uniquement et met à jour les statuts :
    - sent + J+7 → follow_up_needed (+ génère mail de relance)
    - follow_up_sent + J+7 → no_response
    """
    cutoff_7j = datetime.utcnow() - timedelta(days=7)
    updated = []

    # sent → follow_up_needed
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .where(
            Application.status == "sent",
            Application.sent_at <= cutoff_7j,
            Application.user_id == current_user.id,
        )
    )
    apps_to_followup = result.scalars().all()

    for app in apps_to_followup:
        offer = app.job_offer
        company_name = offer.company.name if offer and offer.company else "l'entreprise"
        try:
            followup_content = await _generate_followup_email(
                job_title=offer.title if offer else "le poste",
                company=company_name,
                sent_date=app.sent_at.strftime("%d/%m/%Y") if app.sent_at else "récemment",
                original_email_preview=(app.email_body or "")[:300],
            )
            app.followup_email_body = followup_content.get("body", "")
        except Exception:
            app.followup_email_body = _default_followup_body(
                offer.title if offer else "le poste", company_name
            )
        app.status = "follow_up_needed"
        app.followup_generated_at = datetime.utcnow()
        updated.append({
            "id": str(app.id),
            "offer": offer.title if offer else "N/A",
            "company": company_name,
            "new_status": "follow_up_needed",
            "action_required": "Envoyez le mail de relance manuellement, puis confirmez avec PATCH /{id}/confirm-followup-sent",
        })

    # follow_up_sent → no_response
    result2 = await db.execute(
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .where(
            Application.status == "follow_up_sent",
            Application.followup_sent_at <= cutoff_7j,
            Application.user_id == current_user.id,
        )
    )
    apps_no_response = result2.scalars().all()

    for app in apps_no_response:
        app.status = "no_response"
        offer = app.job_offer
        updated.append({
            "id": str(app.id),
            "offer": offer.title if offer else "N/A",
            "company": offer.company.name if offer and offer.company else "N/A",
            "new_status": "no_response",
        })

    await db.commit()
    return {
        "updated": len(updated),
        "results": updated,
        "message": f"{len(apps_to_followup)} relances à envoyer, {len(apps_no_response)} sans réponse.",
    }


@router.post("/generate/{offer_id}")
async def generate_for_offer(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Génère lettre de motivation + mail pour une offre spécifique.
    La candidature est liée à l'utilisateur connecté.
    """
    result = await db.execute(
        select(JobOffer)
        .options(selectinload(JobOffer.company))
        .where(JobOffer.id == offer_id)
    )
    offer = result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre non trouvée")
    if offer.relevance_score and offer.relevance_score < 60:
        raise HTTPException(status_code=400, detail=f"Score trop bas ({offer.relevance_score}/100)")

    # Récupère le profil pour personnaliser
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    candidate = profile_to_candidate(profile) if profile else None

    generated = await generate_application(offer, candidate)
    application = await create_application_draft(db, offer, generated, current_user.id)
    application.status = "to_apply"
    await db.commit()

    return {
        "application_id": str(application.id),
        "offer": offer.title,
        "company": offer.company.name if offer.company else "Inconnue",
        "offer_url": offer.source_url,
        "status": "to_apply",
        "confidence": generated.get("confidence_score"),
        "email_subject": generated.get("email_subject"),
        "email_body": generated.get("email_body"),
        "cover_letter": generated.get("cover_letter"),
        "personalization": generated.get("personalization_highlights", []),
        "next_action": "Candidatez via le lien, puis PATCH /{application_id}/confirm-sent",
    }


@router.get("/{application_id}")
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .where(
            Application.id == application_id,
            Application.user_id == current_user.id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")
    return {
        "id": str(app.id),
        "offer": app.job_offer.title if app.job_offer else "N/A",
        "company": app.job_offer.company.name if app.job_offer and app.job_offer.company else "N/A",
        "offer_url": app.job_offer.source_url if app.job_offer else None,
        "status": app.status,
        "confidence": app.llm_confidence_score,
        "email_subject": app.email_subject,
        "email_body": app.email_body,
        "cover_letter": app.cover_letter_text,
        "followup_email_body": app.followup_email_body,
        "sent_at": str(app.sent_at) if app.sent_at else None,
        "followup_sent_at": str(app.followup_sent_at) if app.followup_sent_at else None,
        "created_at": str(app.created_at),
    }


# ================================================================
# ROUTES DE CONFIRMATION MANUELLE
# ================================================================

@router.patch("/{application_id}/confirm-sent")
async def confirm_sent(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """L'utilisateur confirme qu'il a candidaté manuellement → statut 'sent'"""
    app = await _get_app(application_id, current_user.id, db)
    if app.status != "to_apply":
        raise HTTPException(status_code=400, detail=f"Statut actuel '{app.status}' — attendu 'to_apply'")
    app.status = "sent"
    app.sent_at = datetime.utcnow()
    await db.commit()
    return {"id": str(app.id), "status": "sent", "sent_at": str(app.sent_at)}


@router.patch("/{application_id}/confirm-followup-sent")
async def confirm_followup_sent(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """L'utilisateur confirme qu'il a envoyé la relance → statut 'follow_up_sent'"""
    app = await _get_app(application_id, current_user.id, db)
    if app.status != "follow_up_needed":
        raise HTTPException(status_code=400, detail=f"Statut actuel '{app.status}' — attendu 'follow_up_needed'")
    app.status = "follow_up_sent"
    app.followup_sent_at = datetime.utcnow()
    await db.commit()
    return {"id": str(app.id), "status": "follow_up_sent", "followup_sent_at": str(app.followup_sent_at)}


@router.patch("/{application_id}/confirm-interview")
async def confirm_interview(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """L'utilisateur confirme un entretien obtenu → statut 'interview'"""
    app = await _get_app(application_id, current_user.id, db)
    app.status = "interview"
    await db.commit()
    return {"id": str(app.id), "status": "interview"}


@router.patch("/{application_id}/confirm-refused")
async def confirm_refused(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """L'utilisateur marque la candidature comme refusée → statut 'refused'"""
    app = await _get_app(application_id, current_user.id, db)
    app.status = "refused"
    await db.commit()
    return {"id": str(app.id), "status": "refused"}


# ================================================================
# HELPERS INTERNES
# ================================================================

async def _get_app(application_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Application:
    """Récupère une candidature en vérifiant qu'elle appartient à l'utilisateur connecté"""
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")
    return app


async def _generate_followup_email(
    job_title: str,
    company: str,
    sent_date: str,
    original_email_preview: str,
) -> dict:
    """Génère le texte de relance via LLM (stocké en base, pas envoyé)"""
    import json
    from pathlib import Path
    from openai import AsyncOpenAI
    from app.config import settings

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    prompt_path = Path(__file__).parent.parent / "prompts" / "write_followup.txt"
    prompt = prompt_path.read_text(encoding="utf-8")
    filled = prompt.format(
        job_title=job_title,
        company=company,
        sent_date=sent_date,
        original_email_preview=original_email_preview,
        full_name="Prénom Nom",
    )
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": filled}],
        temperature=0.3,
        max_tokens=500,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def _default_followup_body(job_title: str, company: str) -> str:
    return (
        f"Madame, Monsieur,\n\n"
        f"Je me permets de revenir vers vous concernant ma candidature au poste de {job_title}, "
        f"que je vous ai adressée il y a une semaine.\n\n"
        f"Toujours très intéressé(e) par cette opportunité et par les projets de {company}, "
        f"je reste disponible pour tout complément d'information ou pour un entretien "
        f"selon votre convenance.\n\n"
        f"Dans l'attente de votre retour, je vous adresse mes cordiales salutations.\n\n"
        f"Prénom Nom"
    )