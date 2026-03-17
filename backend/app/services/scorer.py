"""
Scorer d'offres d'emploi
--------------------------
Utilise le vrai profil utilisateur pour scorer les offres.
"""
from __future__ import annotations
import json
from pathlib import Path
from openai import AsyncOpenAI
from app.models.job_offer import JobOffer
from app.models.profile import Profile
from app.config import settings
import structlog

logger = structlog.get_logger()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def load_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def profile_to_scorer_dict(profile: Profile) -> dict:
    """Convertit un profil en dict pour le scoring"""
    all_skills = []
    for field in [profile.skills_technical, profile.tools, profile.skills, profile.skills_soft]:
        if field and isinstance(field, list):
            all_skills += field

    education_parts = []
    if profile.education_level:
        education_parts.append(profile.education_level)
    if profile.school:
        education_parts.append(profile.school)
    education = ", ".join(education_parts) if education_parts else "Formation non renseignée"

    locations = profile.target_locations if isinstance(profile.target_locations, list) else []
    if profile.location and profile.location not in locations:
        locations.append(profile.location)
    if not locations:
        locations = ["Paris"]

    availability = f"Disponible à partir de {profile.availability_date}" if profile.availability_date else "Disponibilité à préciser"

    return {
        "skills": all_skills if all_skills else ["À compléter"],
        "education": education,
        "locations": locations,
        "availability": availability,
        "target_contract": profile.target_contract or "stage",
    }


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
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error("Erreur analyse offre", error=str(e))
        return {"required_skills": [], "nice_to_have_skills": [], "experience_level": "junior", "key_missions": []}


async def score_offer(offer: JobOffer, profile: dict = None) -> dict:
    """Score une offre par rapport au profil (0-100)"""
    if profile is None:
        profile = {
            "skills": ["À compléter dans le profil"],
            "education": "Non renseigné",
            "locations": ["Paris"],
            "availability": "À préciser",
        }

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
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        score_result = json.loads(raw)
        score_result["analysis"] = analysis
        return score_result
    except Exception as e:
        logger.error("Erreur scoring", error=str(e))
        return {"total_score": 0, "recommendation": "ignorer"}


def get_action(score_result: dict, auto_send_threshold: int = 85, min_score: int = 60) -> str:
    score = score_result.get("total_score", 0)
    if score >= auto_send_threshold:
        return "auto_send"
    elif score >= min_score:
        return "draft"
    return "ignore"
