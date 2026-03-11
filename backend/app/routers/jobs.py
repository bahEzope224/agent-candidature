from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.database import get_db
from app.services.scraper.wttj import scrape_all_queries
from app.services.job_service import save_many_offers
from app.services.scorer import score_offer, get_action
from app.services.indeed_scraper import scrape_indeed
from app.models.job_offer import JobOffer
from app.dependencies import get_current_user
from app.models.user import User
import structlog
import uuid

router = APIRouter()
logger = structlog.get_logger()


@router.post("/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    locations: list[str] = ["Paris"],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    source: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(JobOffer).limit(limit).order_by(JobOffer.scraped_at.desc())
    if status:
        query = query.where(JobOffer.status == status)
    if source:
        query = query.where(JobOffer.source_platform == source)

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


# ── Indeed ─────────────────────────────────────────────────

class IndeedScrapeRequest(BaseModel):
    search_term: str = "Data Analyst stage"
    location: str = "Paris, France"
    results_wanted: int = 20


@router.post("/scrape-indeed")
async def scrape_indeed_jobs(
    body: IndeedScrapeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scrape Indeed et sauvegarde les offres en base"""
    jobs = scrape_indeed(
        search_term=body.search_term,
        location=body.location,
        results_wanted=body.results_wanted,
    )

    if not jobs:
        return {"message": "Aucune offre trouvée", "count": 0}

    saved = 0
    for job in jobs:
        # Vérifie si déjà en base par URL
        existing = await db.execute(
            select(JobOffer).where(JobOffer.source_url == job["url"])
        )
        if existing.scalar_one_or_none():
            continue

        # Crée l'offre
        offer = JobOffer(
            title=job["title"],
            location=job["location"],
            description=job["description"],
            source_url=job["url"],
            source_platform="indeed",
            status="to_review",
        )
        db.add(offer)
        await db.flush()

        # Score GPT
        try:
            score_result = await score_offer(offer)
            offer.relevance_score = score_result.get("total_score", 0)
            offer.score_breakdown = score_result
            offer.analysis_json = score_result.get("analysis", {})
            offer.status = "shortlisted" if get_action(score_result) != "ignore" else "ignored"
        except Exception as e:
            logger.error("Erreur scoring Indeed", error=str(e))
            offer.relevance_score = 0

        saved += 1

    await db.commit()
    return {"message": f"{saved} offres Indeed sauvegardées", "count": saved}