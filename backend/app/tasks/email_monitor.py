from celery import shared_task
from datetime import datetime
import structlog

logger = structlog.get_logger()


@shared_task(name="app.tasks.email_monitor.monitor_inbox")
def monitor_inbox():
    """
    Surveille la boîte mail et détecte les réponses
    liées aux candidatures envoyées.
    """
    from app.services.email_service import get_recent_emails
    from app.models.application import Application
    from app.models.email_thread import EmailThread
    from sqlalchemy import select

    db = None
    try:
        from app.tasks.followups import get_sync_db
        db = get_sync_db()

        # Récupère les emails récents
        emails = get_recent_emails(max_results=20)
        new_responses = 0

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
        logger.info("Surveillance inbox terminée", new_responses=new_responses)
        return {"emails_checked": len(emails), "new_responses": new_responses}

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