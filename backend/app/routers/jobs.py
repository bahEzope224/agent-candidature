from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.services.scraper.wttj import scrape_all_queries
from app.services.job_service import save_many_offers
from app.services.scorer import score_offer, get_action, profile_to_scorer_dict
from app.models.user import User
from app.services.auth_service import get_current_user 
from app.models.profile import Profile
from app.models.job_offer import JobOffer
import structlog
import uuid

router = APIRouter()  # ← doit être avant toutes les routes
logger = structlog.get_logger()


@router.post("/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    locations: list[str] = ["Paris"],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Charge le profil pour personnaliser les requêtes
    profile_result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    # Construit les requêtes depuis le profil
    contract = profile.target_contract or "stage" if profile else "stage"
    queries = []
    if profile and profile.target_roles:
        queries = list(profile.target_roles) 
        for role in profile.target_roles:
            queries.append(f"{role} {contract}")
        
    locs = []
    if profile and profile.target_locations:
        locs = profile.target_locations
    if not locs:
        locs = locations

    async def run_scrape():
        logger.info("Démarrage du scraping", locations=locs, queries=queries)
        raw_offers = await scrape_all_queries(
        locations=locs,
        max_pages=2,
        queries=queries if queries else None,
        contract=contract,  # ← passe le vrai contrat du profil
    )
        stats = await save_many_offers(db, raw_offers, current_user.id)
        logger.info("Scraping terminé", **stats)

    background_tasks.add_task(run_scrape)
    return {"message": "Scraping démarré en arrière-plan"}

@router.get("/")
async def list_offers(
    status: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # ← ajouté
):
    query = (
        select(JobOffer)
        .where(JobOffer.user_id == current_user.id)  # ← filtre par user
        .limit(limit)
        .order_by(JobOffer.scraped_at.desc())
    )
    if status:
        query = query.where(JobOffer.status == status)
    result = await db.execute(query)
    offers = result.scalars().all()
    return [
        {
            "id": str(o.id),
            "title": o.title,
            "location": o.location,
            "platform": o.source_platform,
            "status": o.status,
            "relevance_score": o.relevance_score,
            "url": o.source_url,
        }
        for o in offers
    ]


@router.post("/score-all")
async def score_all_pending(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    result = await db.execute(
        select(JobOffer)
        .options(selectinload(JobOffer.company))
        .where(JobOffer.status == "to_review")
        .where(JobOffer.user_id == current_user.id)        
        .limit(10)
    )
    offers = result.scalars().all()

    # Récupère le profil pour scorer avec les vraies données
    profile_result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    scorer_profile = profile_to_scorer_dict(profile) if profile else None

    results = []
    for offer in offers:
        score_result = await score_offer(offer, scorer_profile)
        action = get_action(score_result)

        offer.relevance_score = score_result.get("total_score", 0)
        offer.score_breakdown = score_result
        offer.analysis_json = score_result.get("analysis", {})
        offer.status = "shortlisted" if action != "ignore" else "ignored"

        results.append({
            "title": offer.title,
            "score": score_result.get("total_score"),
            "action": action,
        })

    await db.commit()
    return {"scored": len(results), "results": results}


@router.post("/{offer_id}/score")
async def score_one_offer(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobOffer)
        .options(selectinload(JobOffer.company))
        .where(JobOffer.id == offer_id)
    )
    offer = result.scalar_one_or_none()

    if not offer:
        raise HTTPException(status_code=404, detail="Offre non trouvée")

    score_result = await score_offer(offer)
    action = get_action(score_result)

    offer.relevance_score = score_result.get("total_score", 0)
    offer.score_breakdown = score_result
    offer.analysis_json = score_result.get("analysis", {})
    offer.status = "shortlisted" if action != "ignore" else "ignored"
    await db.commit()

    return {
        "offer_id": str(offer_id),
        "title": offer.title,
        "score": score_result.get("total_score"),
        "action": action,
        "strengths": score_result.get("strengths", []),
        "gaps": score_result.get("gaps", []),
        "recommendation": score_result.get("recommendation"),
    }

@router.delete("/{offer_id}")
async def delete_offer(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import delete as sql_delete
    from app.models.application import Application

    # Vérifie que l'offre appartient à l'user
    result = await db.execute(
        select(JobOffer).where(
            JobOffer.id == offer_id,
            JobOffer.user_id == current_user.id,
        )
    )
    offer = result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre non trouvée")

    # Supprime les candidatures liées d'abord
    await db.execute(
        sql_delete(Application).where(Application.job_offer_id == offer_id)
    )

    await db.delete(offer)
    await db.commit()
    return {"message": "Offre supprimée"}


@router.delete("/")
async def delete_all_offers(
    status: str = None,  # ← nouveau paramètre optionnel
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import delete as sql_delete
    from app.models.application import Application

    # Filtre par statut si fourni
    query = select(JobOffer.id).where(JobOffer.user_id == current_user.id)
    if status:
        query = query.where(JobOffer.status == status)

    result = await db.execute(query)
    offer_ids = [row[0] for row in result.fetchall()]

    if not offer_ids:
        return {"message": "Aucune offre à supprimer", "deleted": 0}

    await db.execute(
        sql_delete(Application).where(Application.job_offer_id.in_(offer_ids))
    )
    await db.execute(
        sql_delete(JobOffer).where(JobOffer.id.in_(offer_ids))
    )
    await db.commit()
    return {"message": f"{len(offer_ids)} offres supprimées", "deleted": len(offer_ids)}