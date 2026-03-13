# Indeed scraper désactivé — remplacé par Adzuna (wttj.py)
import structlog
logger = structlog.get_logger()

def scrape_indeed(
    search_term: str = "Data Analyst",
    location: str = "Paris, France",
    results_wanted: int = 20,
) -> list[dict]:
    logger.info("Indeed scraper désactivé — utilise Adzuna")
    return []