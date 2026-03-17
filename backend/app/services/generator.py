"""
Générateur de candidatures personnalisées
------------------------------------------
Utilise le vrai profil utilisateur depuis la base de données
pour personnaliser les emails et lettres de motivation.
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


def profile_to_candidate(profile: Profile) -> dict:
    """Convertit un objet Profile SQLAlchemy en dict pour les prompts"""

    # Construit les compétences depuis tous les champs
    all_skills = []
    if profile.skills_technical:
        all_skills += profile.skills_technical if isinstance(profile.skills_technical, list) else []
    if profile.tools:
        all_skills += profile.tools if isinstance(profile.tools, list) else []
    if profile.skills:
        all_skills += profile.skills if isinstance(profile.skills, list) else []

    # Formation
    education_parts = []
    if profile.education_level:
        education_parts.append(profile.education_level)
    if profile.school:
        education_parts.append(profile.school)
    if profile.graduation_year:
        education_parts.append(f"(promo {profile.graduation_year})")
    education = ", ".join(education_parts) if education_parts else "Formation non renseignée"

    # Langues
    languages = []
    if profile.languages:
        for l in (profile.languages if isinstance(profile.languages, list) else []):
            if isinstance(l, dict):
                languages.append(f"{l.get('lang', '')} ({l.get('level', '')})")
            else:
                languages.append(str(l))

    # Disponibilité
    availability = f"Disponible à partir de {profile.availability_date}" if profile.availability_date else "Disponibilité à préciser"

    # Lettre de motivation template depuis le pitch/motivation
    cover_template = ""
    if profile.pitch:
        cover_template += profile.pitch + "\n\n"
    if profile.motivation:
        cover_template += profile.motivation + "\n\n"
    if profile.strengths:
        cover_template += f"Points forts : {profile.strengths}\n\n"
    if not cover_template:
        cover_template = "Madame, Monsieur,\n\nJe souhaite vous adresser ma candidature pour ce poste.\n\nCordialement,"

    full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip() or "Candidat"

    return {
        "full_name": full_name,
        "education": education,
        "skills": all_skills if all_skills else ["À compléter dans le profil"],
        "skills_soft": profile.skills_soft if isinstance(profile.skills_soft, list) else [],
        "languages": languages,
        "availability": availability,
        "duration": 6,
        "linkedin": profile.linkedin_url or "",
        "github": profile.portfolio_url or "",
        "location": profile.location or "Paris",
        "target_roles": profile.target_roles if isinstance(profile.target_roles, list) else [],
        "target_contract": profile.target_contract or "stage",
        "cover_letter_template": cover_template,
    }


async def generate_application(
    offer: JobOffer,
    candidate: dict = None,
) -> dict:
    """Génère un email et une lettre de motivation personnalisés"""

    # Si pas de profil passé, utilise un profil minimal
    if candidate is None:
        candidate = {
            "full_name": "Candidat",
            "education": "Formation non renseignée — complétez votre profil",
            "skills": ["À compléter dans le profil"],
            "availability": "À préciser",
            "duration": 6,
            "linkedin": "",
            "github": "",
            "cover_letter_template": "Madame, Monsieur,\n\nJe vous adresse ma candidature.\n\nCordialement,",
        }

    prompt = load_prompt("generate_application")
    analysis = offer.analysis_json or {}
    score_breakdown = offer.score_breakdown or {}

    filled = prompt.format(
        full_name=candidate["full_name"],
        education=candidate["education"],
        skills=", ".join(candidate["skills"]) if candidate["skills"] else "À compléter",
        availability=candidate["availability"],
        duration=candidate.get("duration", 6),
        linkedin=candidate.get("linkedin", ""),
        github=candidate.get("github", ""),
        job_title=offer.title,
        company=offer.company.name if offer.company else "l'entreprise",
        location=offer.location or "Non précisée",
        required_skills=", ".join(analysis.get("required_skills", [])),
        key_missions=", ".join(analysis.get("key_missions", [])),
        strengths=", ".join(score_breakdown.get("strengths", [])),
        cover_letter_template=candidate["cover_letter_template"],
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": filled}],
            temperature=0.4,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        logger.info("Candidature générée", offer=offer.title, confidence=result.get("confidence_score"))
        return result

    except json.JSONDecodeError as e:
        logger.error("JSON invalide depuis LLM", error=str(e))
        return {
            "email_subject": f"Candidature - {offer.title} - {candidate['full_name']}",
            "email_body": "Erreur de génération — vérifier manuellement",
            "cover_letter": "",
            "confidence_score": 0.0,
            "personalization_highlights": [],
        }
    except Exception as e:
        logger.error("Erreur génération candidature", error=str(e))
        raise
