"""
Scraper via jobspy — Google Jobs + LinkedIn (pas de 403 comme Indeed).
Compatible python-jobspy==1.1.82
"""
import asyncio
import hashlib
from typing import Optional
import structlog

logger = structlog.get_logger()

QUERIES = [
    "Data Analyst stage Paris",
    "Data Scientist stage Paris",
    "Business Analyst Data Paris",
    "Analyste données alternance Paris",
]


def _make_hash(title: str, company: str, url: str) -> str:
    return hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()


def _scrape_sync(query: str, results_wanted: int = 15) -> list[dict]:
    """Scraping via Google Jobs (pas de blocage IP)."""
    try:
        from jobspy import scrape_jobs

        df = scrape_jobs(
            site_name=["google"],
            google_search_term=query,
            results_wanted=results_wanted,
        )

        if df is None or df.empty:
            logger.warning("Jobspy aucun résultat", query=query)
            return []

        offers = []
        for _, row in df.iterrows():
            try:
                title = str(row.get("title") or "")
                company = str(row.get("company") or "")
                url = str(row.get("job_url") or "")
                description = str(row.get("description") or "")[:2000]
                location = str(row.get("location") or "Paris")
                contract = str(row.get("job_type") or "")
                source = str(row.get("site") or "google")

                if not title or not company:
                    continue

                offers.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "contract_type": contract,
                    "description": description,
                    "url": url,
                    "source": source,
                    "hash": _make_hash(title, company, url),
                })
            except Exception as e:
                logger.warning("Erreur parsing row", error=str(e))
                continue

        logger.info("Jobspy résultats", query=query, count=len(offers))
        return offers

    except ImportError:
        logger.error("python-jobspy non installé")
        return []
    except Exception as e:
        logger.error("Erreur jobspy", query=query, error=str(e))
        return []


async def scrape_all_queries(
    locations: Optional[list[str]] = None,
    max_pages: int = 2,
) -> list[dict]:
    """Lance le scraping pour toutes les requêtes."""
    all_offers = []
    seen_hashes = set()
    results_per_query = max(10, max_pages * 10)

    for query in QUERIES:
        logger.info("Scraping requête", query=query)
        try:
            loop = asyncio.get_event_loop()
            offers = await loop.run_in_executor(
                None, _scrape_sync, query, results_per_query
            )
            for o in offers:
                if o["hash"] not in seen_hashes:
                    seen_hashes.add(o["hash"])
                    all_offers.append(o)
        except Exception as e:
            logger.error("Erreur scraping", query=query, error=str(e))

        await asyncio.sleep(2)

    logger.info("Scraping terminé", total=len(all_offers))
    return all_offers


async def scrape_wttj(query: str, location: str = "Paris", max_pages: int = 2) -> list[dict]:
    """Alias pour compatibilité avec l'ancien code."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _scrape_sync, f"{query} stage {location}", max(10, max_pages * 10)
    )