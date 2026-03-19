import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from app.models.user import User
from app.models.application import Application
from app.database import Base

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    website: Mapped[str] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job_offers: Mapped[list["JobOffer"]] = relationship(back_populates="company")


class JobOffer(Base):
    __tablename__ = "job_offers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Infos de l'offre
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    required_skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    nice_to_have_skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    contract_type: Mapped[str] = mapped_column(String(50), default=[])
    duration_months: Mapped[int] = mapped_column(Integer, nullable=True)

    # Source
    source_platform: Mapped[str] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Scoring
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=True)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=True)
    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Statut
    # to_review | shortlisted | to_apply | ignored | expired
    status: Mapped[str] = mapped_column(String(50), default="to_review")

    # Relations
    company: Mapped["Company"] = relationship(back_populates="job_offers")
    applications: Mapped[list["Application"]] = relationship(back_populates="job_offer")
    user: Mapped["User"] = relationship(back_populates="job_offers")