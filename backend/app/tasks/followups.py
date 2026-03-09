from celery import shared_task
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json
import structlog
from app.models.application import Application
from app.models.job_offer import JobOffer, Company
from app.tasks.celery_app import celery_app
import structlog

logger = structlog.get_logger()


def get_sync_db():
    """Session synchrone pour Celery (pas d'async dans les workers)"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    # Convertit l'URL async en sync
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
    Vérifie toutes les candidatures envoyées
    et envoie une relance si J+7 sans réponse.
    """
    db = get_sync_db()
    sent_count = 0
    skipped_count = 0

    try:
        from app.models.application import Application

        # Récupère les candidatures éligibles à une relance
        cutoff_date = datetime.utcnow() - timedelta(days=7)



        applications = db.execute(
            select(Application)
            .options(
                selectinload(Application.job_offer)
                .selectinload(JobOffer.company)
            )
            .where(
                Application.status == "sent",
                Application.sent_at <= cutoff_date,
                Application.followup_sent_at.is_(None),
            )
        ).scalars().all()

        logger.info(
            "Candidatures éligibles relance",
            count=len(applications)
        )

        for app in applications:
            result = send_single_followup(app, db)
            if result:
                sent_count += 1
            else:
                skipped_count += 1

        db.commit()
        logger.info(
            "Relances terminées",
            sent=sent_count,
            skipped=skipped_count,
        )
        return {"sent": sent_count, "skipped": skipped_count}

    except Exception as exc:
        db.rollback()
        logger.error("Erreur check_followups", error=str(exc))
        raise self.retry(exc=exc)
    finally:
        db.close()


def send_single_followup(application, db) -> bool:
    """
    Génère et envoie une relance pour une candidature.
    Retourne True si relance envoyée, False si ignorée.
    """
    from app.services.email_service import create_draft
    from app.models.email_thread import Followup
    import asyncio

    offer = application.job_offer
    if not offer:
        return False

    company_name = offer.company.name if offer.company else "l'entreprise"

    # Vérifie qu'on n'est pas le weekend
    today = datetime.utcnow()
    if today.weekday() >= 5:  # samedi=5, dimanche=6
        logger.info(
            "Relance ignorée — weekend",
            app_id=str(application.id)
        )
        return False

    # Génère le texte de relance via LLM
    try:
        followup_content = asyncio.run(
            generate_followup_text(application, offer, company_name)
        )
    except Exception as e:
        logger.error("Erreur génération relance", error=str(e))
        # Utilise un template par défaut en cas d'erreur LLM
        followup_content = get_default_followup(offer.title, company_name)

    # Crée un brouillon Gmail (plus sûr que l'envoi direct)
    result = create_draft(
        to="recruteur@entreprise.com",  # sera remplacé par le vrai email
        subject=followup_content["subject"],
        body=followup_content["body"],
    )

    if result["success"]:
        # Met à jour le statut de la candidature
        application.status = "follow_up_sent"
        application.followup_sent_at = datetime.utcnow()

        # Enregistre la relance en base
        followup = Followup(
            application_id=application.id,
            scheduled_at=today,
            sent_at=today,
            email_body=followup_content["body"],
            status="sent",
        )
        db.add(followup)

        logger.info(
            "Relance créée",
            company=company_name,
            offer=offer.title,
        )
        return True

    return False


async def generate_followup_text(application, offer, company_name: str) -> dict:
    """Génère le texte de relance via GPT"""
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
        full_name="Prénom Nom",  # sera remplacé par le vrai profil
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


def get_default_followup(job_title: str, company: str) -> dict:
    """Template de relance par défaut si LLM indisponible"""
    return {
        "subject": f"Re : Candidature - Stage {job_title}",
        "body": f"""Madame, Monsieur,

Je me permets de revenir vers vous concernant ma candidature au poste de {job_title}, \
que je vous ai adressée il y a une semaine.

Toujours très intéressé(e) par cette opportunité et par les projets de {company}, \
je reste disponible pour tout complément d'information ou pour un entretien \
selon votre convenance.

Dans l'attente de votre retour, je vous adresse mes cordiales salutations.

Prénom Nom""",
    }