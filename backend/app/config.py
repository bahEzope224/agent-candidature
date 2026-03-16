from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

ENV_FILE = Path(".env") if Path(".env").exists() else Path("../.env")

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    OPENAI_API_KEY: str
    SECRET_KEY: str
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    MAX_APPLICATIONS_PER_DAY: int = 5
    AUTO_SEND_THRESHOLD: int = 85
    MIN_RELEVANCE_SCORE: int = 60
    FOLLOWUP_DAYS: int = 7

    # Gmail
    GMAIL_CREDENTIALS_FILE: str = "gmail_credentials.json"
    GMAIL_TOKEN_FILE: str = "gmail_token.json"
    GMAIL_SENDER_EMAIL: str = ""

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()