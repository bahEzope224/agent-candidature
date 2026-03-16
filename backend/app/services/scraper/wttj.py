import asyncio
import random
from datetime import datetime
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from app.services.scraper.base import RawJobOffer
import structlog

logger = structlog.get_logger()

WTTJ_API = "https://api.welcometothejungle.com/api/v1/organizations"
WTTJ_SEARCH = "https://api.welcometothejungle.com/api/v1/jobs"

SEARCH_QUERIES = [
    "Data Analyst",
    "Data Scientist",
    "Business Analyst",
    "BI Analyst",
    "Data Engineer",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/html",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.welcometothejungle.com/",
}


async def scrape_wttj(
    query: str,
    location: str = "Paris",
    max_pages: int = 2,
) -> list[RawJobOffer]:
    """Scrape les offres WTTJ via l'API publique"""
    offers = []

    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        for page_num in range(1, max_pages + 1):
            params = {
                "query": query,
                "page": page_num,
                "aroundQuery": location,
                "contractType": "internship",
                "sc": "WXncGW",
            }

            url = "https://www.welcometothejungle.com/fr/jobs"
            logger.info("Scraping WTTJ", query=query, location=location, page=page_num)

            try:
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    logger.warning("WTTJ status non-200", status=r.status_code)
                    break

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select('[data-testid="search-results-list-item-wrapper"]')

                # Fallback si WTTJ a changé ses sélecteurs
                if not cards:
                    cards = soup.select('li[class*="job"]') or soup.select('article')

                if not cards:
                    logger.info("Aucune card trouvée", page=page_num)
                    # Essaie d'extraire depuis les balises script JSON-LD
                    offers += _extract_jsonld(soup, location)
                    break

                for card in cards:
                    offer = _extract_card(card, location)
                    if offer:
                        offers.append(offer)

                logger.info("Offres extraites", count=len(offers), page=page_num)
                await asyncio.sleep(random.uniform(1, 2))

            except Exception as e:
                logger.error("Erreur scraping WTTJ", error=str(e))
                break

    return offers


def _extract_card(card, location: str) -> Optional[RawJobOffer]:
    """Extrait les données d'une card HTML"""
    try:
        title_el = card.select_one("h2") or card.select_one("h3")
        title = title_el.get_text(strip=True) if title_el else None

        link_el = card.select_one('a[href*="/jobs/"]') or card.select_one("a")
        href = link_el.get("href", "") if link_el else ""

        img_el = card.select_one("img[alt]")
        company = img_el.get("alt", "Inconnu").strip() if img_el else "Inconnu"

        if not title or not href:
            return None

        source_url = (
            f"https://www.welcometothejungle.com{href}"
            if href.startswith("/") else href
        )

        loc = location
        if "_" in href:
            loc = href.split("_")[-1].replace("-", " ").title()

        return RawJobOffer(
            title=title,
            company_name=company,
            location=loc,
            description="",
            source_url=source_url,
            source_platform="wttj",
            contract_type="stage",
            posted_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.warning("Erreur extraction card", error=str(e))
        return None


def _extract_jsonld(soup, location: str) -> list[RawJobOffer]:
    """Extrait les offres depuis les balises JSON-LD si disponibles"""
    import json
    offers = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                items = data
            elif data.get("@type") == "ItemList":
                items = [e.get("item", {}) for e in data.get("itemListElement", [])]
            else:
                items = [data]

            for item in items:
                if item.get("@type") == "JobPosting":
                    title = item.get("title", "")
                    company = item.get("hiringOrganization", {}).get("name", "Inconnu")
                    url = item.get("url", "")
                    if title and url:
                        offers.append(RawJobOffer(
                            title=title,
                            company_name=company,
                            location=location,
                            description=item.get("description", "")[:500],
                            source_url=url,
                            source_platform="wttj",
                            contract_type="stage",
                            posted_at=datetime.utcnow(),
                        ))
        except Exception:
            continue
    return offers


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

            for offer in offers:
                h = offer.compute_hash()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    all_offers.append(offer)

            await asyncio.sleep(random.uniform(2, 4))

    logger.info("Scraping terminé", total=len(all_offers))
    return all_offers
