from celery import Celery
from celery.schedules import crontab

# Import explicite des settings AVANT création de l'app
from app.config import settings

celery_app = Celery("job_agent")

celery_app.config_from_object({
    "broker_url": settings.REDIS_URL,
    "result_backend": settings.REDIS_URL,
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "Europe/Paris",
    "enable_utc": True,
    "task_track_started": True,
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "include": [
        "app.tasks.followups",
        "app.tasks.email_monitor",
        "app.tasks.scraping",
        "app.tasks.email_tasks",
    ],
    "beat_schedule": {
        "check-followups": {
            "task": "app.tasks.followups.check_and_send_followups",
            "schedule": crontab(hour=9, minute=0),
        },
        "monitor-inbox": {
            "task": "app.tasks.email_monitor.monitor_inbox",
            "schedule": crontab(minute="*/15"),
        },
        "daily-scraping": {
            "task": "app.tasks.scraping.daily_scrape",
            "schedule": crontab(hour=8, minute=0),
        },
    },
})