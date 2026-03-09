import asyncio
import random
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.services.scraper.base import RawJobOffer
import structlog

logger = structlog.get_logger()

WTTJ_BASE = "https://www.welcometothejungle.com/fr/jobs"

SEARCH_QUERIES = [
    "Data Analyst",
    "Data Scientist",
    "Business Analyst",
    "BI Analyst",
    "Data Engineer",
]

async def scrape_wttj(
    query: str,
    location: str = "Paris",
    max_pages: int = 3,
) -> list[RawJobOffer]:
    """Scrape les offres WTTJ pour une requête donnée"""
    offers = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
        )
        page = await context.new_page()

        for page_num in range(1, max_pages + 1):
            url = (
                f"{WTTJ_BASE}?query={query.replace(' ', '+')}"
                f"&page={page_num}"
                f"&aroundQuery={location}"
                f"&contractType=internship"
            )

            logger.info("Scraping WTTJ", url=url, page=page_num)

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(random.uniform(2, 4))  # respecte les serveurs

                # Attend que les cards soient chargées
                await page.wait_for_selector(
                    '[data-testid="search-results-list-item-wrapper"]',
                    timeout=15000
                )

                cards = await page.query_selector_all('[data-testid="search-results-list-item-wrapper"]')

                if not cards:
                    logger.info("Aucune offre sur cette page", page=page_num)
                    break

                for card in cards:
                    offer = await extract_card_data(card, page)
                    if offer:
                        offers.append(offer)

                logger.info("Offres trouvées", count=len(cards), page=page_num)

            except PlaywrightTimeout:
                logger.warning("Timeout WTTJ", page=page_num, url=url)
                break
            except Exception as e:
                logger.error("Erreur scraping WTTJ", error=str(e), page=page_num)
                break

            # Pause entre pages (évite le ban)
            await asyncio.sleep(random.uniform(3, 6))

        await browser.close()

    return offers


async def extract_card_data(card, page) -> Optional[RawJobOffer]:
    """Extrait les données d'une card WTTJ"""
    try:
        # Titre — dans le h2
        title_el = await card.query_selector('h2')
        title = await title_el.inner_text() if title_el else None

        # Entreprise — dans le alt de l'image logo
        img_el = await card.query_selector('img[alt]')
        company = await img_el.get_attribute('alt') if img_el else "Inconnu"

        # URL — premier lien de la card
        link_el = await card.query_selector('a[href*="/jobs/"]')
        href = await link_el.get_attribute('href') if link_el else None

        if not title or not href:
            return None

        # Localisation — extraite depuis l'URL (ex: senior-data-analyst_paris)
        # Format WTTJ : /fr/companies/slug/jobs/job-title_ville
        location = ""
        if "_" in href:
            location_slug = href.split("_")[-1]  # ex: "paris"
            location = location_slug.replace("-", " ").title()

        source_url = (
            f"https://www.welcometothejungle.com{href}"
            if href.startswith("/") else href
        )

        return RawJobOffer(
            title=title.strip(),
            company_name=company.strip(),
            location=location.strip(),
            description="",
            source_url=source_url,
            source_platform="wttj",
            contract_type="stage",
            posted_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.warning("Erreur extraction card WTTJ", error=str(e))
        return None


async def scrape_all_queries(
    locations: list[str] = None,
    max_pages: int = 2,
) -> list[RawJobOffer]:
    """Lance le scraping pour toutes les requêtes et localisations"""
    if locations is None:
        locations = ["Paris"]

    all_offers = []
    seen_hashes = set()

    for query in SEARCH_QUERIES:
        for location in locations:
            logger.info("Scraping requête", query=query, location=location)
            offers = await scrape_wttj(query, location, max_pages)

            # Déduplication par hash
            for offer in offers:
                h = offer.compute_hash()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    all_offers.append(offer)

            # Pause entre requêtes
            await asyncio.sleep(random.uniform(5, 10))

    logger.info("Scraping terminé", total=len(all_offers))
    return all_offers