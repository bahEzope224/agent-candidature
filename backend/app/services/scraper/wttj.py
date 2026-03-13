"""
Scraper via API Adzuna — API publique gratuite, pas de blocage IP.
Nécessite ADZUNA_APP_ID et ADZUNA_APP_KEY dans les variables d'env.
"""
import asyncio
import hashlib
import os
from typing import Optional
import httpx
import structlog

logger = structlog.get_logger()

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs/fr/search"

QUERIES = [
    "Data Analyst stage",
    "Data Scientist stage",
    "Business Intelligence Analyst",
    "Analyste données alternance",
]


def _make_hash(title: str, company: str, url: str) -> str:
    return hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()


async def _scrape_adzuna(
    query: str,
    location: str = "Paris",
    results_wanted: int = 20,
) -> list[dict]:
    """Scrape via l'API Adzuna."""
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        logger.error("ADZUNA_APP_ID / ADZUNA_APP_KEY manquants dans les variables d'env")
        return []

    offers = []
    pages = max(1, results_wanted // 20)

    async with httpx.AsyncClient(timeout=30) as client:
        for page in range(1, pages + 1):
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": 20,
                "what": query,
                "where": location,
                "content-type": "application/json",
            }
            try:
                r = await client.get(f"{ADZUNA_BASE}/{page}", params=params)
                if r.status_code != 200:
                    logger.warning("Adzuna erreur HTTP", status=r.status_code, query=query)
                    break

                data = r.json()
                jobs = data.get("results", [])
                if not jobs:
                    break

                for job in jobs:
                    title = job.get("title", "")
                    company = (job.get("company") or {}).get("display_name", "")
                    url = job.get("redirect_url", "")
                    description = job.get("description", "")[:2000]
                    loc = (job.get("location") or {}).get("display_name", location)
                    contract = job.get("contract_time", "")

                    if not title:
                        continue

                    offers.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "contract_type": contract,
                        "description": description,
                        "url": url,
                        "source": "adzuna",
                        "hash": _make_hash(title, company, url),
                    })

                logger.info("Adzuna page scrapée", query=query, page=page, count=len(jobs))
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error("Adzuna erreur", query=query, error=str(e))
                break

    return offers


async def scrape_all_queries(
    locations: Optional[list[str]] = None,
    max_pages: int = 2,
) -> list[dict]:
    """Lance le scraping pour toutes les requêtes."""
    if locations is None:
        locations = ["Paris"]

    all_offers = []
    seen_hashes = set()
    results_per_query = max(20, max_pages * 20)

    for query in QUERIES:
        for location in locations:
            logger.info("Scraping requête", query=query, location=location)
            try:
                offers = await _scrape_adzuna(query, location, results_per_query)
                for o in offers:
                    if o["hash"] not in seen_hashes:
                        seen_hashes.add(o["hash"])
                        all_offers.append(o)
            except Exception as e:
                logger.error("Erreur scraping", query=query, error=str(e))
            await asyncio.sleep(1)

    logger.info("Scraping terminé", total=len(all_offers))
    return all_offers


async def scrape_wttj(query: str, location: str = "Paris", max_pages: int = 2) -> list[dict]:
    """Alias pour compatibilité."""
    return await _scrape_adzuna(query, location, max(20, max_pages * 20))