from celery import shared_task
import structlog

logger = structlog.get_logger()


@shared_task(name="app.tasks.email_tasks.send_email_task", bind=True, max_retries=3)
def send_email_task(self, to: str, subject: str, body: str):
    """Envoie un email via Gmail en arrière-plan"""
    try:
        from app.services.email_service import send_email
        result = send_email(to=to, subject=subject, body=body)
        
        if not result.get("success"):
            raise Exception(result.get("error", "Erreur inconnue"))
        
        logger.info("Email envoyé via Celery", to=to, subject=subject)
        return result

    except Exception as e:
        logger.error("Erreur envoi email", error=str(e), to=to)
        raise self.retry(exc=e, countdown=60)  # réessaie dans 60s


@shared_task(name="app.tasks.email_tasks.send_application_email", bind=True, max_retries=3)
def send_application_email_task(self, application_id: str):
    """Envoie une candidature par email en arrière-plan"""
    import asyncio

    async def run():
        from app.database import AsyncSessionLocal
        from app.models.application import Application
        from app.services.email_service import send_email, create_draft
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Application).where(
                    Application.id == application_id
                )
            )
            application = result.scalar_one_or_none()

            if not application:
                logger.error("Candidature introuvable", id=application_id)
                return {"error": "Candidature introuvable"}

            # Envoie ou crée brouillon selon le seuil
            if application.relevance_score >= 85:
                result = send_email(
                    to=application.contact_email or "recruteur@entreprise.com",
                    subject=application.subject,
                    body=application.body,
                )
                application.status = "sent"
            else:
                result = create_draft(
                    to=application.contact_email or "",
                    subject=application.subject,
                    body=application.body,
                )
                application.status = "draft"

            await db.commit()
            logger.info("Candidature traitée", id=application_id, status=application.status)
            return result

    return asyncio.run(run())


@shared_task(name="app.tasks.email_tasks.send_bulk_applications")
def send_bulk_applications_task(application_ids: list):
    """Envoie plusieurs candidatures en batch"""
    results = []
    for app_id in application_ids:
        result = send_application_email_task.delay(app_id)
        results.append({"application_id": app_id, "task_id": result.id})
    
    logger.info("Batch candidatures lancé", count=len(application_ids))
    return results