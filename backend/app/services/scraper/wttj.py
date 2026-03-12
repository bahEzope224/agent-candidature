"""
Scraper WTTJ sans Playwright — utilise l'API publique Welcome to the Jungle.
Fonctionne sur Render free tier (pas de Chromium nécessaire).
"""
import asyncio
import hashlib
import logging
from typing import Optional
import httpx
import structlog

logger = structlog.get_logger()

WTTJ_API = "https://api.welcometothejungle.com/api/v1"
HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.welcometothejungle.com/",
    "Origin": "https://www.welcometothejungle.com",
}

QUERIES = [
    "Data Analyst",
    "Data Scientist",
    "Business Intelligence",
    "Analyste données",
]


def _make_hash(title: str, company: str, url: str) -> str:
    return hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()


async def scrape_wttj(
    query: str,
    location: str = "Paris",
    max_pages: int = 2,
) -> list[dict]:
    """Scrape WTTJ via son API publique pour une requête donnée."""
    offers = []
    params_base = {
        "query": query,
        "page": 1,
        "per_page": 30,
        "contract_type[]": ["internship", "apprenticeship", "full_time"],
    }

    # Ajout localisation si précisée
    if location and location.lower() not in ("france", "remote", ""):
        params_base["location_geopoint"] = location
        params_base["aroundRadius"] = 50

    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            params = {**params_base, "page": page}
            try:
                logger.info("WTTJ API request", query=query, location=location, page=page)
                r = await client.get(f"{WTTJ_API}/jobs", params=params)

                if r.status_code == 200:
                    data = r.json()
                    jobs = data.get("jobs", [])
                    if not jobs:
                        break

                    for job in jobs:
                        try:
                            org = job.get("organization", {}) or {}
                            contract = job.get("contract_type", "") or ""
                            slug = job.get("slug", "") or job.get("reference", "")
                            org_slug = org.get("slug", "") or ""
                            url = (
                                f"https://www.welcometothejungle.com/fr/companies/"
                                f"{org_slug}/jobs/{slug}"
                                if org_slug and slug
                                else "https://www.welcometothejungle.com"
                            )

                            title = job.get("name", "") or ""
                            company = org.get("name", "") or ""
                            description = job.get("description", "") or ""
                            location_data = job.get("office", {}) or {}
                            city = location_data.get("city", location) or location

                            offers.append({
                                "title": title,
                                "company": company,
                                "location": city,
                                "contract_type": contract,
                                "description": description[:2000],
                                "url": url,
                                "source": "wttj",
                                "hash": _make_hash(title, company, url),
                            })
                        except Exception as e:
                            logger.warning("Erreur parsing job", error=str(e))
                            continue

                    logger.info("WTTJ page scrapée", query=query, page=page, count=len(jobs))

                    # Pagination
                    total_pages = data.get("meta", {}).get("total_pages", 1)
                    if page >= total_pages:
                        break

                elif r.status_code == 429:
                    logger.warning("WTTJ rate limit", page=page)
                    await asyncio.sleep(5)
                    break
                else:
                    logger.warning("WTTJ erreur HTTP", status=r.status_code, page=page)
                    # Fallback : essaie l'API de recherche alternative
                    offers_alt = await _scrape_wttj_search(client, query, location, page)
                    offers.extend(offers_alt)
                    break

            except httpx.TimeoutException:
                logger.warning("WTTJ timeout", query=query, page=page)
                break
            except Exception as e:
                logger.error("WTTJ erreur", query=query, error=str(e))
                break

            await asyncio.sleep(1)  # politesse

    return offers


async def _scrape_wttj_search(
    client: httpx.AsyncClient,
    query: str,
    location: str,
    page: int = 1,
) -> list[dict]:
    """Fallback : API de recherche WTTJ alternative."""
    offers = []
    try:
        params = {
            "query": query,
            "page": page,
            "per_page": 20,
        }
        r = await client.get(
            "https://api.welcometothejungle.com/api/v1/jobs/search",
            params=params,
        )
        if r.status_code == 200:
            data = r.json()
            for job in data.get("jobs", []):
                org = job.get("organization", {}) or {}
                title = job.get("name", "")
                company = org.get("name", "")
                url = f"https://www.welcometothejungle.com/fr/jobs/{job.get('slug','')}"
                offers.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "contract_type": job.get("contract_type", ""),
                    "description": (job.get("description", "") or "")[:2000],
                    "url": url,
                    "source": "wttj",
                    "hash": _make_hash(title, company, url),
                })
    except Exception as e:
        logger.warning("WTTJ fallback erreur", error=str(e))
    return offers


async def scrape_all_queries(
    locations: Optional[list[str]] = None,
    max_pages: int = 2,
) -> list[dict]:
    """Lance le scraping pour toutes les requêtes et localisations."""
    if locations is None:
        locations = ["Paris"]

    all_offers = []
    seen_hashes = set()

    for query in QUERIES:
        for location in locations:
            logger.info("Scraping requête", query=query, location=location)
            try:
                offers = await scrape_wttj(query, location, max_pages)
                for o in offers:
                    if o["hash"] not in seen_hashes:
                        seen_hashes.add(o["hash"])
                        all_offers.append(o)
            except Exception as e:
                logger.error("Erreur scraping", query=query, location=location, error=str(e))
            await asyncio.sleep(2)

    logger.info("Scraping terminé", total=len(all_offers))
    return all_offers