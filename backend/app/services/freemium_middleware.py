"""
Utilitaires freemium — à importer dans les routers concernés.
Incrémente les compteurs et vérifie les quotas.
"""
from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, check_scraping_quota, check_application_quota, check_scoring_quota


async def enforce_scraping_quota(user: User, db: AsyncSession) -> None:
    """Vérifie et incrémente le quota scraping. Lève 429 si dépassé."""
    allowed, msg = check_scraping_quota(user)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    today = date.today()
    if user.scraping_date != today:
        user.scraping_count_today = 0
        user.scraping_date = today

    user.scraping_count_today += 1
    await db.commit()


async def enforce_application_quota(user: User, db: AsyncSession) -> None:
    """Vérifie et incrémente le quota candidatures. Lève 429 si dépassé."""
    allowed, msg = check_application_quota(user)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    today = date.today()
    if user.applications_month != today.month or user.applications_year != today.year:
        user.applications_count_month = 0
        user.applications_month = today.month
        user.applications_year = today.year

    user.applications_count_month += 1
    await db.commit()


async def enforce_scoring_quota(user: User, db: AsyncSession) -> None:
    """Vérifie et incrémente le quota scoring. Lève 429 si dépassé."""
    allowed, msg = check_scoring_quota(user)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    today = date.today()
    if user.scoring_date != today:
        user.scoring_count_today = 0
        user.scoring_date = today

    user.scoring_count_today += 1
    await db.commit()


def get_quota_status(user: User) -> dict:
    """Retourne le statut des quotas pour affichage dans le dashboard."""
    from app.models.user import FREEMIUM_LIMITS, PREMIUM_LIMITS
    limits = PREMIUM_LIMITS if user.is_premium else FREEMIUM_LIMITS
    today = date.today()

    scraping_used = user.scraping_count_today if user.scraping_date == today else 0
    scoring_used = user.scoring_count_today if user.scoring_date == today else 0
    apps_used = (
        user.applications_count_month
        if user.applications_month == today.month and user.applications_year == today.year
        else 0
    )

    return {
        "is_premium": user.is_premium,
        "scraping": {
            "used": scraping_used,
            "limit": limits["max_scrapings_per_day"],
            "remaining": max(0, limits["max_scrapings_per_day"] - scraping_used),
        },
        "applications": {
            "used": apps_used,
            "limit": limits["max_applications_per_month"],
            "remaining": max(0, limits["max_applications_per_month"] - apps_used),
        },
        "scoring": {
            "used": scoring_used,
            "limit": limits["max_scoring_per_day"],
            "remaining": max(0, limits["max_scoring_per_day"] - scoring_used),
        },
    }