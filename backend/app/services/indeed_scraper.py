from jobspy import scrape_jobs
import pandas as pd
import structlog

logger = structlog.get_logger()


def scrape_indeed(
    search_term: str = "Data Analyst",
    location: str = "Paris, France",
    results_wanted: int = 20,
) -> list[dict]:
    """Scrape Indeed via jobspy"""
    try:
        jobs = scrape_jobs(
            site_name=["indeed"],
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=72,
            country_indeed="France",
        )

        if jobs.empty:
            logger.info("Aucun résultat Indeed", search_term=search_term)
            return []

        results = []
        for _, row in jobs.iterrows():
            results.append({
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "location": str(row.get("location", "")),
                "contract_type": str(row.get("job_type", "")) or "Non précisé",
                "description": str(row.get("description", ""))[:3000],
                "url": str(row.get("job_url", "")),
                "salary": str(row.get("min_amount", "")) or None,
                "source": "indeed",
            })

        logger.info("Indeed scrapé", count=len(results))
        return results

    except Exception as e:
        logger.error("Erreur scraping Indeed", error=str(e))
        return []