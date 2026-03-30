import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Boolean, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from typing import TYPE_CHECKING
from app.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.job_offer import JobOffer
    from app.models.profile import Profile


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # Statut du compte
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Plan
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)

    # Compteurs freemium
    scraping_count_today: Mapped[int] = mapped_column(Integer, default=0)
    scraping_date: Mapped[date] = mapped_column(Date, nullable=True)
    applications_count_month: Mapped[int] = mapped_column(Integer, default=0)
    applications_month: Mapped[int] = mapped_column(Integer, nullable=True)  # mois courant (1-12)
    applications_year: Mapped[int] = mapped_column(Integer, nullable=True)   # année courante
    scoring_count_today: Mapped[int] = mapped_column(Integer, default=0)
    scoring_date: Mapped[date] = mapped_column(Date, nullable=True)

    # Sécurité
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    job_offers: Mapped[list["JobOffer"]] = relationship(back_populates="user")
    applications: Mapped[list["Application"]] = relationship(back_populates="user")
    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)


# ── Limites freemium ──────────────────────────────────────────
FREEMIUM_LIMITS = {
    "max_scrapings_per_day": 2,
    "max_applications_per_month": 5,
    "max_scoring_per_day": 10,
}

PREMIUM_LIMITS = {
    "max_scrapings_per_day": 999,
    "max_applications_per_month": 999,
    "max_scoring_per_day": 999,
}


def get_limits(user: "User") -> dict:
    return PREMIUM_LIMITS if user.is_premium else FREEMIUM_LIMITS


def check_scraping_quota(user: "User") -> tuple[bool, str]:
    """Retourne (autorisé, message_erreur)"""
    limits = get_limits(user)
    today = date.today()

    # Reset si nouveau jour
    if user.scraping_date != today:
        return True, ""

    if user.scraping_count_today >= limits["max_scrapings_per_day"]:
        if user.is_premium:
            return True, ""
        return False, f"Limite atteinte : {limits['max_scrapings_per_day']} scrapings/jour en version gratuite. Passez en Premium pour scraper sans limite."
    return True, ""


def check_application_quota(user: "User") -> tuple[bool, str]:
    """Retourne (autorisé, message_erreur)"""
    limits = get_limits(user)
    today = date.today()

    # Reset si nouveau mois
    if user.applications_month != today.month or user.applications_year != today.year:
        return True, ""

    if user.applications_count_month >= limits["max_applications_per_month"]:
        if user.is_premium:
            return True, ""
        return False, f"Limite atteinte : {limits['max_applications_per_month']} candidatures/mois en version gratuite. Passez en Premium pour candidater sans limite."
    return True, ""


def check_scoring_quota(user: "User") -> tuple[bool, str]:
    """Retourne (autorisé, message_erreur)"""
    limits = get_limits(user)
    today = date.today()

    if user.scoring_date != today:
        return True, ""

    if user.scoring_count_today >= limits["max_scoring_per_day"]:
        if user.is_premium:
            return True, ""
        return False, f"Limite atteinte : {limits['max_scoring_per_day']} scorings/jour en version gratuite. Passez en Premium pour scorer sans limite."
    return True, ""