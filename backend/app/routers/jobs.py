from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.services.scraper.wttj import scrape_all_queries
from app.services.job_service import save_many_offers
from app.services.scorer import score_offer, get_action
from app.models.job_offer import JobOffer
from app.models.user import User
from app.services.auth_service import get_current_user
import structlog
import uuid

router = APIRouter()  # ← doit être avant toutes les routes
logger = structlog.get_logger()


@router.post("/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    locations: list[str] = ["Paris"],
    db: AsyncSession = Depends(get_db),
):
    async def run_scrape():
        logger.info("Démarrage du scraping", locations=locations)
        raw_offers = await scrape_all_queries(locations=locations, max_pages=2)
        stats = await save_many_offers(db, raw_offers)
        logger.info("Scraping terminé", **stats)

    background_tasks.add_task(run_scrape)
    return {"message": "Scraping démarré en arrière-plan"}


@router.get("/")
async def list_offers(
    status: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(JobOffer).limit(limit).order_by(JobOffer.scraped_at.desc())
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
):
    result = await db.execute(
        select(JobOffer)
        .options(selectinload(JobOffer.company))
        .where(JobOffer.status == "to_review")
        .limit(10)
    )
    offers = result.scalars().all()

    results = []
    for offer in offers:
        score_result = await score_offer(offer)
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
    """Supprime une offre de l'utilisateur connecté"""
    result = await db.execute(
        select(JobOffer).where(
            JobOffer.id == offer_id,
            JobOffer.user_id == current_user.id,
        )
    )
    offer = result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offre non trouvée")
    await db.delete(offer)
    await db.commit()
    return {"message": "Offre supprimée"}


@router.delete("/")
async def delete_all_offers(
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Supprime toutes les offres de l'utilisateur connecté.
    Optionnel : filtrer par statut (ex: ?status=ignored)
    """
    from sqlalchemy import delete as sql_delete
    query = sql_delete(JobOffer).where(JobOffer.user_id == current_user.id)
    if status:
        query = query.where(JobOffer.status == status)
    result = await db.execute(query)
    await db.commit()
    return {"message": f"{result.rowcount} offre(s) supprimée(s)"}
