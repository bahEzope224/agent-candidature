"""
Scraper basé sur l'API Adzuna
-------------------------------
Adzuna est une API gratuite (inscription requise sur developer.adzuna.com)
Variables d'environnement requises :
  ADZUNA_APP_ID  
  ADZUNA_APP_KEY 
"""
import asyncio
import random
from datetime import datetime
from typing import Optional
import httpx
from app.services.scraper.base import RawJobOffer
from app.config import settings
import structlog

logger = structlog.get_logger()

CONTRACT_MAP = {
    "stage": "internship",
    "alternance": "contract",
    "cdi": "permanent",
    "cdd": "contract",
}

async def scrape_adzuna(
    query: str,
    location: str = "Paris",
    contract: str = "stage",
    max_pages: int = 2,
) -> list[RawJobOffer]:
    offers = []
    app_id = getattr(settings, "ADZUNA_APP_ID", "")
    app_key = getattr(settings, "ADZUNA_APP_KEY", "")

    if not app_id or not app_key:
        logger.warning("Clés Adzuna manquantes — configurez ADZUNA_APP_ID et ADZUNA_APP_KEY sur Render")
        return []

    async with httpx.AsyncClient(timeout=15) as client:
        for page in range(1, max_pages + 1):
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": 20,
                "what": query,
                "where": location,
                "content-type": "application/json",
            }
            url = f"https://api.adzuna.com/v1/api/jobs/fr/search/{page}"
            logger.info("Scraping Adzuna", query=query, location=location, page=page)
            try:
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    logger.warning("Adzuna status non-200", status=r.status_code)
                    break
                data = r.json()
                results = data.get("results", [])
                if not results:
                    break
                for job in results:
                    offer = _parse_adzuna(job)
                    if offer:
                        offers.append(offer)
                logger.info("Offres Adzuna", count=len(results), page=page)
                await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                logger.error("Erreur Adzuna", error=str(e))
                break
    return offers


def _parse_adzuna(job: dict) -> Optional[RawJobOffer]:
    try:
        title = job.get("title", "").strip()
        company = job.get("company", {}).get("display_name", "Inconnu").strip()
        location = job.get("location", {}).get("display_name", "").strip()
        description = job.get("description", "")[:500]
        url = job.get("redirect_url", "")
        created = job.get("created", "")
        if not title or not url:
            return None
        posted_at = None
        if created:
            try:
                posted_at = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                posted_at = datetime.utcnow()
        return RawJobOffer(
            title=title,
            company_name=company,
            location=location,
            description=description,
            source_url=url,
            source_platform="adzuna",
            contract_type="stage",
            posted_at=posted_at or datetime.utcnow(),
        )
    except Exception as e:
        logger.warning("Erreur parse Adzuna", error=str(e))
        return None


async def scrape_wttj(
    query: str,
    location: str = "Paris",
    max_pages: int = 2,
    contract: str = "stage",
) -> list[RawJobOffer]:
    """Alias pour compatibilité"""
    return await scrape_adzuna(query, location, contract, max_pages)


async def scrape_all_queries(
    queries: list[str] = None,
    locations: list[str] = None,
    contract: str = "stage",
    max_pages: int = 2,
) -> list[RawJobOffer]:
    if queries is None:
        queries = ["Data Analyst"]
    if locations is None:
        locations = ["Paris"]

    all_offers = []
    seen_hashes = set()

    for query in queries:
        full_query = f"{contract} {query}" if contract not in query.lower() else query
        for location in locations:
            logger.info("Scraping requête", query=full_query, location=location)
            offers = await scrape_adzuna(full_query, location, contract, max_pages)
            for offer in offers:
                h = offer.compute_hash()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    all_offers.append(offer)
            await asyncio.sleep(random.uniform(1, 2))

    logger.info("Scraping terminé", total=len(all_offers))
    return all_offers
