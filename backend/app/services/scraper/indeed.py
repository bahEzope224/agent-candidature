import asyncio
import random
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.services.scraper.base import RawJobOffer
import structlog

logger = structlog.get_logger()

SEARCH_QUERIES = [
    "stage data analyst",
    "stage data scientist",
    "stage business analyst data",
    "stage BI analyst",
]

async def scrape_indeed(
    query: str,
    location: str = "Paris",
    max_pages: int = 3,
) -> list[RawJobOffer]:
    offers = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
        )
        page = await context.new_page()

        for page_num in range(max_pages):
            start = page_num * 10
            url = (
                f"https://fr.indeed.com/jobs"
                f"?q={query.replace(' ', '+')}"
                f"&l={location}"
                f"&start={start}"
                f"&fromage=14"  # offres des 14 derniers jours
            )

            logger.info("Scraping Indeed", query=query, page=page_num + 1)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(3, 5))

                # Sélecteurs Indeed (stables)
                cards = await page.query_selector_all('[data-testid="slider_item"]')

                if not cards:
                    # Fallback sélecteur
                    cards = await page.query_selector_all('.job_seen_beacon')

                if not cards:
                    logger.warning("Aucune card trouvée", page=page_num + 1)
                    break

                for card in cards:
                    offer = await extract_indeed_card(card)
                    if offer:
                        offers.append(offer)

                logger.info("Offres extraites", count=len(cards), page=page_num + 1)

            except PlaywrightTimeout:
                logger.warning("Timeout Indeed", page=page_num + 1)
                break
            except Exception as e:
                logger.error("Erreur Indeed", error=str(e))
                break

            await asyncio.sleep(random.uniform(4, 8))

        await browser.close()

    return offers


async def extract_indeed_card(card) -> Optional[RawJobOffer]:
    try:
        # Titre
        title_el = await card.query_selector('[data-testid="jobsearch-ResultsList"] h2 a, h2.jobTitle a, h2 a')
        title = await title_el.inner_text() if title_el else None

        # Entreprise
        company_el = await card.query_selector('[data-testid="company-name"], .companyName')
        company = await company_el.inner_text() if company_el else "Inconnu"

        # Localisation
        loc_el = await card.query_selector('[data-testid="text-location"], .companyLocation')
        location = await loc_el.inner_text() if loc_el else ""

        # URL
        link_el = await card.query_selector('h2 a')
        href = await link_el.get_attribute('href') if link_el else None

        if not title or not href:
            return None

        source_url = (
            f"https://fr.indeed.com{href}"
            if href.startswith("/") else href
        )

        return RawJobOffer(
            title=title.strip(),
            company_name=company.strip(),
            location=location.strip(),
            description="",
            source_url=source_url,
            source_platform="indeed",
            contract_type="stage",
            posted_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.warning("Erreur extraction card Indeed", error=str(e))
        return None


async def scrape_all_indeed(
    locations: list[str] = None,
    max_pages: int = 2,
) -> list[RawJobOffer]:
    if locations is None:
        locations = ["Paris"]

    all_offers = []
    seen_hashes = set()

    for query in SEARCH_QUERIES:
        for location in locations:
            offers = await scrape_indeed(query, location, max_pages)
            for offer in offers:
                h = offer.compute_hash()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    all_offers.append(offer)
            await asyncio.sleep(random.uniform(5, 10))

    logger.info("Indeed scraping terminé", total=len(all_offers))
    return all_offers