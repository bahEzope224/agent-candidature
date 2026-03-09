import json
from pathlib import Path
from openai import AsyncOpenAI
from app.models.job_offer import JobOffer
from app.config import settings
import structlog

logger = structlog.get_logger()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Profil par défaut — sera remplacé par les vraies données utilisateur
DEFAULT_CANDIDATE = {
    "full_name": "Prénom Nom",
    "education": "Master 2 Data Science, Université Paris-Saclay (2024-2025)",
    "skills": ["Python", "SQL", "Power BI", "Pandas", "Scikit-learn", "Excel", "Git"],
    "availability": "Disponible à partir de juin 2025",
    "duration": 6,
    "linkedin": "linkedin.com/in/prenom-nom",
    "github": "github.com/prenom-nom",
    "cover_letter_template": """
Madame, Monsieur,

Actuellement étudiant(e) en Master Data Science, je souhaite mettre mes compétences
en Python, SQL et analyse de données au service de vos projets.

Mon parcours m'a permis de développer une solide maîtrise des outils data
et une approche rigoureuse de l'analyse statistique.

Je serais ravi(e) d'échanger sur ma candidature et reste disponible
pour tout entretien selon votre convenance.

Cordialement,
""",
}


def load_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


async def generate_application(
    offer: JobOffer,
    candidate: dict = None,
) -> dict:
    """Génère un email et une lettre de motivation personnalisés"""
    if candidate is None:
        candidate = DEFAULT_CANDIDATE

    prompt = load_prompt("generate_application")

    # Extrait les infos du scoring si disponible
    analysis = offer.analysis_json or {}
    score_breakdown = offer.score_breakdown or {}

    filled = prompt.format(
        full_name=candidate["full_name"],
        education=candidate["education"],
        skills=", ".join(candidate["skills"]),
        availability=candidate["availability"],
        duration=candidate["duration"],
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

        # Nettoie les éventuels backticks markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)
        logger.info(
            "Candidature générée",
            offer=offer.title,
            confidence=result.get("confidence_score"),
        )
        return result

    except json.JSONDecodeError as e:
        logger.error("JSON invalide depuis LLM", error=str(e))
        return {
            "email_subject": f"Candidature - Stage {offer.title}",
            "email_body": "Erreur de génération — vérifier manuellement",
            "cover_letter": "",
            "confidence_score": 0.0,
            "personalization_highlights": [],
        }
    except Exception as e:
        logger.error("Erreur génération candidature", error=str(e))
        raise