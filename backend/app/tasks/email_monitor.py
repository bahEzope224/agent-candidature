from celery import shared_task
from datetime import datetime
from email.utils import parsedate_to_datetime
import structlog

from app.config import settings
from app.services.email_service import get_recent_emails, get_recent_sent_messages

logger = structlog.get_logger()


@shared_task(name="app.tasks.email_monitor.monitor_inbox")
def monitor_inbox():
    """
    Surveille la boîte mail et détecte les réponses
    liées aux candidatures envoyées.
    """
    from app.models.application import Application
    from app.models.email_thread import EmailThread
    from sqlalchemy import select

    db = None
    try:
        from app.tasks.followups import get_sync_db
        db = get_sync_db()

        sent_messages = get_recent_sent_messages(max_results=20)
        emails = get_recent_emails(max_results=20)
        new_responses = 0
        sent_updates = 0

        for sent in sent_messages:
            existing_sent = db.execute(
                select(EmailThread).where(
                    EmailThread.message_id == sent["id"]
                )
            ).scalar_one_or_none()

            if existing_sent:
                continue

            application = find_application_for_sent(sent, db)
            if not application:
                continue

            # Met à jour la candidature en fonction du statut courant
            _apply_sent_status(application, sent)

            # Sauvegarde l'email envoyé dans le fil de discussion
            sent_thread = EmailThread(
                application_id=application.id,
                thread_id=sent["thread_id"],
                message_id=sent["id"],
                direction="sent",
                sender=settings.GMAIL_SENDER_EMAIL or "me",
                recipient=sent.get("to"),
                subject=sent["subject"],
                body_preview=sent["snippet"],
                received_at=datetime.utcnow(),
                is_processed=True,
            )
            db.add(sent_thread)
            sent_updates += 1
            logger.info(
                "Email candidat détecté",
                subject=sent["subject"],
                status=application.status,
            )

        for email in emails:
            # Vérifie si cet email est déjà traité
            existing = db.execute(
                select(EmailThread).where(
                    EmailThread.message_id == email["id"]
                )
            ).scalar_one_or_none()

            if existing:
                continue

            # Cherche la candidature associée
            application = find_related_application(email, db)
            if not application:
                continue

            # Enregistre le thread email
            thread = EmailThread(
                application_id=application.id,
                thread_id=email["thread_id"],
                message_id=email["id"],
                direction="received",
                sender=email["from"],
                subject=email["subject"],
                body_preview=email["snippet"],
                received_at=datetime.utcnow(),
                is_processed=False,
            )
            db.add(thread)

            # Met à jour le statut de la candidature
            if application.status in ["sent", "follow_up_sent"]:
                application.status = "response_received"
                new_responses += 1
                logger.info(
                    "Réponse détectée",
                    company=email["from"],
                    subject=email["subject"],
                )

        db.commit()
        logger.info(
            "Surveillance inbox terminée",
            new_responses=new_responses,
            sent_updates=sent_updates,
        )
        return {
            "emails_checked": len(emails),
            "new_responses": new_responses,
            "sent_detected": sent_updates,
        }

    except Exception as e:
        if db:
            db.rollback()
        logger.error("Erreur monitor_inbox", error=str(e))
        return {"error": str(e)}
    finally:
        if db:
            db.close()


def find_related_application(email: dict, db) -> object:
    """
    Cherche la candidature liée à un email reçu.
    Stratégies : thread_id > domaine expéditeur > mots-clés sujet
    """
    from app.models.application import Application
    from app.models.job_offer import JobOffer, Company
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Stratégie 1 : thread Gmail identique
    if email.get("thread_id"):
        result = db.execute(
            select(Application).where(
                Application.gmail_thread_id == email["thread_id"]
            )
        ).scalar_one_or_none()
        if result:
            return result

    # Stratégie 2 : domaine email expéditeur
    sender = email.get("from", "")
    if "@" in sender:
        domain = sender.split("@")[-1].rstrip(">").strip()

        # Cherche une entreprise avec ce domaine
        company = db.execute(
            select(Company).where(Company.domain.ilike(f"%{domain}%"))
        ).scalar_one_or_none()

        if company:
            result = db.execute(
                select(Application)
                .join(JobOffer)
                .where(
                    JobOffer.company_id == company.id,
                    Application.status.in_(["sent", "follow_up_sent"]),
                )
                .order_by(Application.sent_at.desc())
            ).scalar_one_or_none()
            if result:
                return result

    return None


def find_application_for_sent(email: dict, db):
    """Tente de retrouver la candidature liée à un email envoyé."""
    from app.models.application import Application
    from sqlalchemy import select

    thread_id = email.get("thread_id")
    if thread_id:
        app = db.execute(
            select(Application).where(Application.gmail_thread_id == thread_id)
        ).scalar_one_or_none()
        if app:
            return app

    normalized = _normalize_subject(email.get("subject", ""))
    if not normalized:
        return None

    result = db.execute(
        select(Application)
        .where(Application.status.in_(["to_apply", "follow_up_needed"]))
        .order_by(Application.created_at.desc())
    ).scalars().all()

    for application in result:
        subject = application.email_subject or ""
        if _normalize_subject(subject) == normalized:
            return application

    return None


def _normalize_subject(subject: str) -> str:
    if not subject:
        return ""
    cleaned = subject.lower().strip()
    prefixes = ("re:", "re :", "fw:", "fw :")
    while True:
        moved = False
        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                moved = True
        if not moved:
            break
    return cleaned


def _apply_sent_status(application, email: dict):
    ts = _parse_email_date(email.get("date")) or datetime.utcnow()
    if application.status == "to_apply":
        application.status = "sent"
        if not application.sent_at:
            application.sent_at = ts
    elif application.status == "follow_up_needed":
        application.status = "follow_up_sent"
        application.followup_sent_at = ts
    application.gmail_thread_id = email.get("thread_id")
    application.gmail_message_id = email.get("id")


def _parse_email_date(value: str):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
