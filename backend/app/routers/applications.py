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
from app.services.classifier import classify_email, generate_interview_response, generate_info_response
from app.services.email_service import get_email_body, create_draft
from app.models.email_thread import EmailThread
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

@router.post("/classify-responses")
async def classify_all_responses(
    db: AsyncSession = Depends(get_db),
):
    """
    Lit les emails non traités et les classifie.
    Génère des brouillons de réponse pour les cas positifs.
    """
    from datetime import datetime

    result = await db.execute(
        select(EmailThread)
        .options(
            selectinload(EmailThread.application)
            .selectinload(Application.job_offer)
            .selectinload(JobOffer.company)
        )
        .where(EmailThread.is_processed == False)
        .where(EmailThread.direction == "received")
    )
    threads = result.scalars().all()

    if not threads:
        return {"message": "Aucun email non traité", "classified": 0}

    classified = []

    for thread in threads:
        app = thread.application
        if not app or not app.job_offer:
            continue

        offer = app.job_offer
        company = offer.company.name if offer.company else "Inconnue"

        # Récupère le corps complet depuis Gmail
        full_body = thread.full_body or thread.body_preview or ""
        if not full_body and thread.message_id:
            full_body = get_email_body(thread.message_id)

        # Classifie avec GPT
        classification = await classify_email(
            email_body=full_body,
            email_subject=thread.subject or "",
            sender=thread.sender or "",
            job_title=offer.title,
            company=company,
            sent_date=str(app.sent_at.date()) if app.sent_at else "inconnue",
        )

        # Met à jour le thread
        thread.classification = classification.get("classification")
        thread.classification_confidence = classification.get("confidence")
        thread.is_processed = True

        # Met à jour le statut de la candidature
        cls = classification.get("classification")

        if cls == "refusal":
            app.status = "refused"
            classified.append({
                "company": company,
                "classification": "refusal",
                "action": "Archivé automatiquement",
            })

        elif cls == "interview_request":
            app.status = "interview_proposed"
            # Génère un brouillon de réponse
            response = await generate_interview_response(
                email_body=full_body,
                email_subject=thread.subject or "",
                job_title=offer.title,
                company=company,
            )
            draft = create_draft(
                to=thread.sender or "",
                subject=response.get("subject", ""),
                body=response.get("body", ""),
            )
            classified.append({
                "company": company,
                "classification": "interview_request",
                "action": "Brouillon de réponse créé",
                "draft_id": draft.get("draft_id"),
                "proposed_slots": response.get("proposed_slots", []),
            })

        elif cls == "info_request":
            app.status = "response_received"
            response = await generate_info_response(
                email_body=full_body,
                email_subject=thread.subject or "",
                job_title=offer.title,
                company=company,
            )
            draft = create_draft(
                to=thread.sender or "",
                subject=response.get("subject", ""),
                body=response.get("body", ""),
            )
            classified.append({
                "company": company,
                "classification": "info_request",
                "action": "Brouillon de réponse créé",
                "draft_id": draft.get("draft_id"),
            })

        elif cls in ["positive_interest", "start_date_discussion"]:
            app.status = "response_received"
            classified.append({
                "company": company,
                "classification": cls,
                "action": "Validation humaine requise",
                "urgency": classification.get("urgency"),
                "key_elements": classification.get("key_elements", []),
            })

        else:
            classified.append({
                "company": company,
                "classification": "unclassified",
                "action": "Vérification manuelle recommandée",
            })

    await db.commit()
    return {"classified": len(classified), "results": classified}

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