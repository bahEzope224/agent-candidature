import json
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings
import structlog

logger = structlog.get_logger()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Disponibilités par défaut — à personnaliser
DEFAULT_AVAILABILITY = [
    "Lundi et mardi matin (9h-12h)",
    "Mercredi toute la journée",
    "Vendredi après-midi (14h-17h)",
]


def load_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


async def classify_email(
    email_body: str,
    email_subject: str,
    sender: str,
    job_title: str,
    company: str,
    sent_date: str,
) -> dict:
    """Classifie un email entrant avec GPT"""
    prompt = load_prompt("classify_email")

    filled = prompt.format(
        job_title=job_title,
        company=company,
        sent_date=sent_date,
        sender=sender,
        subject=email_subject,
        body=email_body[:2000],  # limite la taille
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": filled}],
            temperature=0.1,
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        logger.info(
            "Email classifié",
            classification=result.get("classification"),
            confidence=result.get("confidence"),
            company=company,
        )
        return result

    except Exception as e:
        logger.error("Erreur classification email", error=str(e))
        return {
            "classification": "unclassified",
            "confidence": 0.0,
            "sentiment": "neutral",
            "requires_action": False,
            "urgency": "low",
            "draft_needed": False,
        }


async def generate_interview_response(
    email_body: str,
    email_subject: str,
    job_title: str,
    company: str,
    full_name: str = "Prénom Nom",
    availability: list = None,
) -> dict:
    """Génère une réponse à une invitation d'entretien"""
    if availability is None:
        availability = DEFAULT_AVAILABILITY

    prompt = load_prompt("respond_interview")

    filled = prompt.format(
        email_body=email_body[:1500],
        full_name=full_name,
        available_slots="\n".join(f"- {s}" for s in availability),
        job_title=job_title,
        company=company,
        subject=email_subject,
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": filled}],
            temperature=0.3,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    except Exception as e:
        logger.error("Erreur génération réponse entretien", error=str(e))
        return {
            "subject": f"Re : {email_subject}",
            "body": "Erreur de génération — veuillez répondre manuellement",
            "proposed_slots": [],
        }


async def generate_info_response(
    email_body: str,
    email_subject: str,
    job_title: str,
    company: str,
    full_name: str = "Prénom Nom",
) -> dict:
    """Génère une réponse à une demande d'informations"""
    prompt = f"""
Tu assistes {full_name} pour repondre a une demande d'informations
sur sa candidature pour le poste {job_title} chez {company}.

Email recu : {email_body[:1500]}

Redige une reponse professionnelle qui :
1. Repond precisement aux questions posees
2. Reste concis et clair
3. Confirme l'interet pour le poste
4. Propose un entretien si pertinent

Retourne UNIQUEMENT ce JSON :
{{
  "subject": "Re : {email_subject}",
  "body": "Corps complet de la reponse"
}}
"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error("Erreur génération réponse info", error=str(e))
        return {
            "subject": f"Re : {email_subject}",
            "body": "Erreur — veuillez répondre manuellement",
        }


def check_no_reply_received(application) -> bool:
    """Vérifie si une réponse a déjà été reçue pour cette candidature"""
    if not application.email_threads:
        return False
    return any(
        t.direction == "received"
        for t in application.email_threads
    )