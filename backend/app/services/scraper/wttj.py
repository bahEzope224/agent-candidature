"""
Scraper principal — utilise jobspy pour Indeed + LinkedIn.
Pas de Playwright, pas de Chromium, fonctionne sur Render free tier.
"""
import asyncio
import hashlib
from typing import Optional
import structlog

logger = structlog.get_logger()

QUERIES = [
    "Data Analyst",
    "Data Scientist",
    "Business Intelligence Analyst",
    "Analyste données",
]


def _make_hash(title: str, company: str, url: str) -> str:
    return hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()


def _scrape_jobspy_sync(query: str, location: str, results_wanted: int = 20) -> list[dict]:
    """Scraping synchrone via jobspy (Indeed + LinkedIn)."""
    try:
        from jobspy import scrape_jobs

        # Essaie Indeed, fallback LinkedIn si 403
        try:
            df = scrape_jobs(
                site_name=["indeed"],
                search_term=query,
                location=location,
                results_wanted=results_wanted,
            )
        except Exception as e1:
            if "403" in str(e1) or "bad response" in str(e1).lower():
                logger.warning("Indeed 403, fallback LinkedIn", query=query)
                df = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=query,
                    location=location,
                    results_wanted=results_wanted,
                )
            else:
                raise

        if df is None or df.empty:
            logger.warning("Jobspy aucun résultat", query=query, location=location)
            return []

        offers = []
        for _, row in df.iterrows():
            try:
                title = str(row.get("title") or "")
                company = str(row.get("company") or "")
                url = str(row.get("job_url") or "")
                description = str(row.get("description") or "")[:2000]
                job_location = str(row.get("location") or location)
                contract = str(row.get("job_type") or "")
                source = str(row.get("site") or "indeed")

                if not title or not company:
                    continue

                offers.append({
                    "title": title,
                    "company": company,
                    "location": job_location,
                    "contract_type": contract,
                    "description": description,
                    "url": url,
                    "source": source,
                    "hash": _make_hash(title, company, url),
                })
            except Exception as e:
                logger.warning("Erreur parsing row", error=str(e))
                continue

        logger.info("Jobspy résultats", query=query, location=location, count=len(offers))
        return offers

    except ImportError:
        logger.error("jobspy non installé — ajoute python-jobspy dans requirements.txt")
        return []
    except Exception as e:
        err = str(e)
        if "403" in err or "bad response" in err.lower():
            logger.warning("Jobspy 403 — Indeed bloque, skip", query=query)
        else:
            logger.error("Erreur jobspy", query=query, error=err)
        return []


async def scrape_all_queries(
    locations: Optional[list[str]] = None,
    max_pages: int = 2,
) -> list[dict]:
    """Lance le scraping pour toutes les requêtes et localisations."""
    if locations is None:
        locations = ["Paris, France"]

    normalized = [
        f"{loc}, France" if "france" not in loc.lower() else loc
        for loc in locations
    ]

    all_offers = []
    seen_hashes = set()
    results_per_query = max(10, max_pages * 10)

    for query in QUERIES:
        for location in normalized:
            logger.info("Scraping requête", query=query, location=location)
            try:
                loop = asyncio.get_event_loop()
                offers = await loop.run_in_executor(
                    None, _scrape_jobspy_sync, query, location, results_per_query
                )
                for o in offers:
                    if o["hash"] not in seen_hashes:
                        seen_hashes.add(o["hash"])
                        all_offers.append(o)
            except Exception as e:
                logger.error("Erreur scraping", query=query, location=location, error=str(e))

            await asyncio.sleep(3)

    logger.info("Scraping terminé", total=len(all_offers))
    return all_offers


async def scrape_wttj(query: str, location: str = "Paris", max_pages: int = 2) -> list[dict]:
    """Alias pour compatibilité avec l'ancien code."""
    loc = f"{location}, France" if "france" not in location.lower() else location
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _scrape_jobspy_sync, query, loc, max(10, max_pages * 10)
    )