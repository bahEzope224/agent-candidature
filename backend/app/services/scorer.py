import json
from pathlib import Path
from openai import AsyncOpenAI
from app.models.job_offer import JobOffer
from app.config import settings
import structlog

logger = structlog.get_logger()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Ton profil — on externalisera ça en base plus tard
DEFAULT_PROFILE = {
    "skills": ["Python", "SQL", "Excel", "Power BI", "Pandas", "Machine Learning"],
    "education": "Etudiant en Master Data Science / Statistiques",
    "locations": ["Paris", "Île-de-France", "Remote"],
    "availability": "Disponible dès juin 2025",
}

def load_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


async def analyze_offer(offer: JobOffer) -> dict:
    """Analyse une offre avec GPT pour extraire les infos clés"""
    prompt = load_prompt("analyze_offer")

    filled = prompt.format(
        title=offer.title,
        company=offer.company.name if offer.company else "Inconnue",
        description=offer.description or f"Poste : {offer.title}",
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": filled}],
            temperature=0.1,
            max_tokens=800,
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        logger.error("Erreur analyse offre", error=str(e), offer_id=str(offer.id))
        return {"required_skills": [], "nice_to_have_skills": [], "experience_level": "junior"}


async def score_offer(offer: JobOffer, profile: dict = None) -> dict:
    """Score une offre par rapport au profil (0-100)"""
    if profile is None:
        profile = DEFAULT_PROFILE

    # Analyse d'abord l'offre
    analysis = await analyze_offer(offer)

    prompt = load_prompt("score_offer")

    filled = prompt.format(
        skills=", ".join(profile["skills"]),
        education=profile["education"],
        locations=", ".join(profile["locations"]),
        availability=profile["availability"],
        title=offer.title,
        company=offer.company.name if offer.company else "Inconnue",
        location=offer.location or "Non précisée",
        required_skills=", ".join(analysis.get("required_skills", [])),
        nice_to_have_skills=", ".join(analysis.get("nice_to_have_skills", [])),
        experience_level=analysis.get("experience_level", "junior"),
        key_missions=", ".join(analysis.get("key_missions", [])),
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": filled}],
            temperature=0.1,
            max_tokens=600,
        )
        score_result = json.loads(response.choices[0].message.content)
        score_result["analysis"] = analysis  # on garde l'analyse aussi
        return score_result

    except Exception as e:
        logger.error("Erreur scoring", error=str(e), offer_id=str(offer.id))
        return {"total_score": 0, "recommendation": "ignorer"}


def get_action(score_result: dict, auto_send_threshold: int = 85, min_score: int = 60) -> str:
    """
    Retourne l'action recommandée :
    - auto_send  : score >= 85
    - draft      : score entre 60 et 84
    - ignore     : score < 60
    """
    score = score_result.get("total_score", 0)
    if score >= auto_send_threshold:
        return "auto_send"
    elif score >= min_score:
        return "draft"
    return "ignore"