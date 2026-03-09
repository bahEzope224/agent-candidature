from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.job_offer import JobOffer
from app.models.application import Application
from app.services.generator import generate_application
from app.services.job_service import create_application_draft
from app.services.email_service import send_email, create_draft
import uuid

router = APIRouter()


# ================================================================
# ROUTES STATIQUES — doivent être AVANT /{application_id}
# ================================================================

@router.get("/")
async def list_applications(
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .order_by(Application.created_at.desc())
    )
    if status:
        query = query.where(Application.status == status)
    result = await db.execute(query)
    apps = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "offer": a.job_offer.title if a.job_offer else "N/A",
            "company": a.job_offer.company.name if a.job_offer and a.job_offer.company else "N/A",
            "status": a.status,
            "confidence": a.llm_confidence_score,
            "requires_validation": a.requires_human_validation,
            "created_at": str(a.created_at),
            "email_subject": a.email_subject,
        }
        for a in apps
    ]


@router.get("/pending-followups")
async def pending_followups(db: AsyncSession = Depends(get_db)):
    """Liste les candidatures qui attendent une relance"""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .where(
            Application.status == "sent",
            Application.sent_at <= cutoff,
            Application.followup_sent_at.is_(None),
        )
    )
    apps = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "offer": a.job_offer.title if a.job_offer else "N/A",
            "company": a.job_offer.company.name if a.job_offer and a.job_offer.company else "N/A",
            "sent_at": str(a.sent_at),
            "days_since_sent": (datetime.utcnow() - a.sent_at).days if a.sent_at else 0,
        }
        for a in apps
    ]


@router.post("/generate-batch")
async def generate_batch(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
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
    mock_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    for offer in offers:
        try:
            generated = await generate_application(offer)
            application = await create_application_draft(db, offer, generated, mock_user_id)
            results.append({
                "offer": offer.title,
                "company": offer.company.name if offer.company else "Inconnue",
                "score": offer.relevance_score,
                "confidence": generated.get("confidence_score"),
                "status": application.status,
            })
            offer.status = "to_apply"
        except Exception as e:
            results.append({"offer": offer.title, "error": str(e)})
    await db.commit()
    return {"generated": len(results), "results": results}


@router.post("/trigger-followups")
async def trigger_followups():
    """Déclenche manuellement la vérification des relances"""
    from app.tasks.followups import check_and_send_followups
    task = check_and_send_followups.delay()
    return {"message": "Vérification des relances lancée", "task_id": task.id}


# ================================================================
# ROUTES DYNAMIQUES — après les routes statiques
# ================================================================

@router.post("/generate/{offer_id}")
async def generate_for_offer(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
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
    generated = await generate_application(offer)
    confidence = generated.get("confidence_score", 0)
    mock_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    application = await create_application_draft(db, offer, generated, mock_user_id)
    await db.commit()
    return {
        "application_id": str(application.id),
        "offer": offer.title,
        "company": offer.company.name if offer.company else "Inconnue",
        "status": application.status,
        "confidence": confidence,
        "action": "auto_send" if confidence >= 0.85 else "pending_review",
        "email_subject": generated.get("email_subject"),
        "email_preview": generated.get("email_body", "")[:300] + "...",
        "personalization": generated.get("personalization_highlights", []),
    }


@router.get("/{application_id}")
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")
    return {
        "id": str(app.id),
        "offer": app.job_offer.title if app.job_offer else "N/A",
        "company": app.job_offer.company.name if app.job_offer and app.job_offer.company else "N/A",
        "status": app.status,
        "confidence": app.llm_confidence_score,
        "requires_validation": app.requires_human_validation,
        "email_subject": app.email_subject,
        "email_body": app.email_body,
        "cover_letter": app.cover_letter_text,
        "created_at": str(app.created_at),
    }


@router.post("/{application_id}/send")
async def send_application(
    application_id: uuid.UUID,
    mode: str = "draft",
    recipient_email: str = "",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job_offer).selectinload(JobOffer.company))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Candidature non trouvée")
    if app.status not in ["ready_to_send", "pending_review"]:
        raise HTTPException(status_code=400, detail=f"Statut '{app.status}' — ne peut pas être envoyé")
    to_email = recipient_email or "recruteur@entreprise.com"
    if mode == "send":
        email_result = send_email(to=to_email, subject=app.email_subject, body=app.email_body)
        if email_result["success"]:
            from datetime import datetime
            app.status = "sent"
            app.sent_at = datetime.utcnow()
            app.gmail_thread_id = email_result.get("thread_id")
            app.gmail_message_id = email_result.get("message_id")
            await db.commit()
            return {"status": "sent", "message_id": email_result.get("message_id")}
        raise HTTPException(status_code=500, detail=email_result.get("error"))
    else:
        draft_result = create_draft(to=to_email, subject=app.email_subject, body=app.email_body)
        if draft_result["success"]:
            app.status = "pending_review"
            await db.commit()
            return {
                "status": "draft_created",
                "draft_id": draft_result.get("draft_id"),
                "message": "Brouillon créé dans Gmail — vérifie avant d'envoyer",
            }
        raise HTTPException(status_code=500, detail=draft_result.get("error"))