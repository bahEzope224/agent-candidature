# config.py mis à jour avec les variables Stripe
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

ENV_FILE = Path(".env") if Path(".env").exists() else Path("../.env")

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = ""
    OPENAI_API_KEY: str
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    FOLLOWUP_DAYS: int = 7
    MAX_APPLICATIONS_PER_DAY: int = 5
    AUTO_SEND_THRESHOLD: int = 85
    MIN_RELEVANCE_SCORE: int = 60

    # Adzuna
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    # Gmail
    GMAIL_CREDENTIALS_FILE: str = "gmail_credentials.json"
    GMAIL_TOKEN_FILE: str = "gmail_token.json"
    GMAIL_SENDER_EMAIL: str = ""

    # ── Stripe ───────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_NORMAL: str = ""   # price_xxx 2.99€/semaine
    STRIPE_PRICE_PROMO: str = ""    # price_xxx 1.99€/semaine
    FRONTEND_URL: str = "https://job-agent-ibrahima.netlify.app"

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
