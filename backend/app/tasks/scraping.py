from celery import shared_task
import structlog

logger = structlog.get_logger()


@shared_task(name="app.tasks.scraping.daily_scrape")
def daily_scrape():
    """Scraping quotidien automatique à 8h"""
    import asyncio
    from app.services.scraper.wttj import scrape_all_queries

    async def run():
        from app.database import AsyncSessionLocal
        from app.services.job_service import save_many_offers

        logger.info("Démarrage scraping quotidien")
        offers = await scrape_all_queries(
            locations=["Paris", "Lyon", "Remote"],
            max_pages=2,
        )
        async with AsyncSessionLocal() as db:
            stats = await save_many_offers(db, offers)

        logger.info("Scraping quotidien terminé", **stats)
        return stats

    return asyncio.run(run())