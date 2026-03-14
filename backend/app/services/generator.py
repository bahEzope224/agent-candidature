import json
from pathlib import Path
from openai import AsyncOpenAI
from app.models.job_offer import JobOffer
from app.config import settings
import structlog

logger = structlog.get_logger()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def profile_to_candidate(profile) -> dict:
    """Convertit un objet Profile DB en dict candidat pour le générateur."""
    if profile is None:
        return _default_candidate()

    skills = []
    if profile.skills_technical:
        skills += profile.skills_technical
    if profile.tools:
        skills += profile.tools

    languages = []
    if profile.languages:
        for lang in profile.languages:
            if isinstance(lang, dict):
                languages.append(f"{lang.get('lang','')} ({lang.get('level','')})")
            else:
                languages.append(str(lang))

    full_name = " ".join(filter(None, [profile.first_name, profile.last_name])) or "Candidat"
    education = " ".join(filter(None, [profile.education_level, profile.school])) or "Formation non précisée"
    if profile.graduation_year:
        education += f" ({profile.graduation_year})"

    cover_template = _build_cover_template(profile, full_name, skills)

    return {
        "full_name": full_name,
        "education": education,
        "skills": skills or ["Python", "SQL", "Data Analysis"],
        "availability": profile.availability_date or "Disponible dès maintenant",
        "duration": 6,
        "linkedin": profile.linkedin_url or "",
        "github": profile.portfolio_url or "",
        "pitch": profile.pitch or "",
        "strengths": profile.strengths or "",
        "motivation": profile.motivation or "",
        "target_contract": profile.target_contract or "stage",
        "languages": ", ".join(languages),
        "cover_letter_template": cover_template,
    }


def _build_cover_template(profile, full_name: str, skills: list) -> str:
    pitch = profile.pitch or f"étudiant(e) en {profile.education_level or 'Data Science'}"
    strengths = profile.strengths or "une solide maîtrise des outils data"
    motivation = profile.motivation or "passionné(e) par la data et l'analyse"
    skills_str = ", ".join(skills[:5]) if skills else "Python, SQL, analyse de données"
    contract = profile.target_contract or "stage"

    return f"""Madame, Monsieur,

{pitch}

Mes compétences en {skills_str} ainsi que {strengths} me permettent d'être rapidement opérationnel(le).

{motivation}

Je serais ravi(e) d'échanger sur ma candidature pour ce {contract} et reste disponible pour tout entretien.

Cordialement,
{full_name}"""


def _default_candidate() -> dict:
    """Candidat générique si aucun profil n'est trouvé."""
    return {
        "full_name": "Candidat",
        "education": "Master Data Science",
        "skills": ["Python", "SQL", "Power BI", "Pandas", "Scikit-learn"],
        "availability": "Disponible dès maintenant",
        "duration": 6,
        "linkedin": "",
        "github": "",
        "pitch": "",
        "strengths": "",
        "motivation": "",
        "target_contract": "stage",
        "languages": "Français (natif), Anglais (courant)",
        "cover_letter_template": "Madame, Monsieur,\n\nJe vous adresse ma candidature...\n\nCordialement,",
    }


def load_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


async def generate_application(
    offer: JobOffer,
    candidate: dict = None,
) -> dict:
    """Génère un email et une lettre de motivation personnalisés."""
    if candidate is None:
        candidate = _default_candidate()

    analysis = offer.analysis_json or {}
    score_breakdown = offer.score_breakdown or {}

    # Construit le prompt directement sans fichier externe si load_prompt échoue
    try:
        prompt_template = load_prompt("generate_application")
        filled = prompt_template.format(
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
    except Exception:
        # Prompt inline si le fichier n'existe pas
        filled = _build_inline_prompt(offer, candidate, analysis, score_breakdown)

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
            "email_subject": f"Candidature — {candidate['target_contract'].capitalize()} {offer.title}",
            "email_body": candidate["cover_letter_template"],
            "cover_letter": candidate["cover_letter_template"],
            "confidence_score": 0.5,
            "personalization_highlights": [],
        }
    except Exception as e:
        logger.error("Erreur génération candidature", error=str(e))
        raise


def _build_inline_prompt(offer, candidate, analysis, score_breakdown) -> str:
    company = offer.company.name if offer.company else "l'entreprise"
    return f"""Tu es un expert en recrutement. Génère une candidature personnalisée en JSON.

PROFIL DU CANDIDAT :
- Nom : {candidate['full_name']}
- Formation : {candidate['education']}
- Compétences : {', '.join(candidate['skills'])}
- Disponibilité : {candidate['availability']}
- LinkedIn : {candidate.get('linkedin', 'N/A')}
- GitHub/Portfolio : {candidate.get('github', 'N/A')}
- Pitch : {candidate.get('pitch', 'N/A')}
- Points forts : {candidate.get('strengths', 'N/A')}
- Motivation : {candidate.get('motivation', 'N/A')}
- Type de contrat recherché : {candidate.get('target_contract', 'stage')}
- Langues : {candidate.get('languages', 'N/A')}

OFFRE D'EMPLOI :
- Poste : {offer.title}
- Entreprise : {company}
- Localisation : {offer.location or 'Non précisée'}
- Description : {(offer.description or '')[:800]}

Retourne UNIQUEMENT ce JSON valide :
{{
  "email_subject": "Objet de l'email (max 80 chars)",
  "email_body": "Email professionnel complet (300-500 mots), personnalisé avec le vrai nom et les vraies compétences",
  "cover_letter": "Lettre de motivation complète (400-600 mots)",
  "confidence_score": 0.85,
  "personalization_highlights": ["Point personnalisé 1", "Point personnalisé 2"]
}}"""