"""
Tâche Celery — Vérification des délais de relance
---------------------------------------------------
MODE MANUEL : Cette tâche ne fait plus d'envoi automatique.
Elle se contente de :
1. Passer les candidatures "sent" en "follow_up_needed" après J+7
2. Générer le mail de relance et le stocker en base (à copier-coller)
3. Passer les candidatures "follow_up_sent" en "no_response" après J+7

L'envoi automatique est temporairement désactivé.
"""

from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import structlog
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


def get_sync_db():
    """Session synchrone pour Celery (pas d'async dans les workers)"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg2://"
    )
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(
    name="app.tasks.followups.check_and_send_followups",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,
)
def check_and_send_followups(self):
    """
    Vérifie les délais et met à jour les statuts sans envoi automatique.
    - sent + J+7 → follow_up_needed + génère le mail de relance en base
    - follow_up_sent + J+7 → no_response
    """
    db = get_sync_db()
    followup_needed_count = 0
    no_response_count = 0

    try:
        cutoff_7j = datetime.utcnow() - timedelta(days=7)

        # 1. sent → follow_up_needed
        applications_to_flag = db.execute(
            select(Application)
            .options(
                selectinload(Application.job_offer)
                .selectinload(JobOffer.company)
            )
            .where(
                Application.status == "sent",
                Application.sent_at <= cutoff_7j,
            )
        ).scalars().all()

        logger.info("Candidatures à passer en follow_up_needed", count=len(applications_to_flag))

        for app in applications_to_flag:
            result = flag_followup_needed(app, db)
            if result:
                followup_needed_count += 1

        # 2. follow_up_sent → no_response
        applications_no_response = db.execute(
            select(Application)
            .options(
                selectinload(Application.job_offer)
                .selectinload(JobOffer.company)
            )
            .where(
                Application.status == "follow_up_sent",
                Application.followup_sent_at <= cutoff_7j,
            )
        ).scalars().all()

        logger.info("Candidatures à passer en no_response", count=len(applications_no_response))

        for app in applications_no_response:
            app.status = "no_response"
            no_response_count += 1
            logger.info(
                "Statut → no_response",
                offer=app.job_offer.title if app.job_offer else "N/A",
            )

        db.commit()
        logger.info(
            "Vérification délais terminée",
            follow_up_needed=followup_needed_count,
            no_response=no_response_count,
        )
        return {
            "follow_up_needed": followup_needed_count,
            "no_response": no_response_count,
        }

    except Exception as exc:
        db.rollback()
        logger.error("Erreur check_followups", error=str(exc))
        raise self.retry(exc=exc)
    finally:
        db.close()


def flag_followup_needed(application, db) -> bool:
    """
    Passe une candidature en 'follow_up_needed' et génère le mail
    de relance en base (NE l'envoie PAS).
    Retourne True si mis à jour, False si ignoré.
    """
    import asyncio

    offer = application.job_offer
    if not offer:
        return False

    company_name = offer.company.name if offer.company else "l'entreprise"

    # Ne pas traiter le weekend
    today = datetime.utcnow()
    if today.weekday() >= 5:
        logger.info("Ignoré — weekend", app_id=str(application.id))
        return False

    # Génère le texte de relance via LLM et le stocke en base
    try:
        followup_content = asyncio.run(
            generate_followup_text(application, offer, company_name)
        )
        application.followup_email_body = followup_content.get("body", "")
    except Exception as e:
        logger.error("Erreur génération relance", error=str(e))
        application.followup_email_body = get_default_followup_body(
            offer.title, company_name
        )

    application.status = "follow_up_needed"
    application.followup_generated_at = today

    logger.info(
        "Statut → follow_up_needed (mail de relance généré, non envoyé)",
        company=company_name,
        offer=offer.title,
    )
    return True


async def generate_followup_text(application, offer, company_name: str) -> dict:
    """Génère le texte de relance via LLM — stocké en base, pas envoyé"""
    import json
    from pathlib import Path
    from openai import AsyncOpenAI
    from app.config import settings

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    prompt_path = Path(__file__).parent.parent / "prompts" / "write_followup.txt"
    prompt = prompt_path.read_text(encoding="utf-8")

    sent_date = application.sent_at.strftime("%d/%m/%Y") if application.sent_at else "récemment"
    email_preview = (application.email_body or "")[:300]

    filled = prompt.format(
        job_title=offer.title,
        company=company_name,
        sent_date=sent_date,
        original_email_preview=email_preview,
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


def get_default_followup_body(job_title: str, company: str) -> str:
    """Template de relance par défaut si LLM indisponible"""
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