import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.database import Base

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Cibles de recherche
    target_roles: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=["Data Analyst", "Data Scientist"]
    )
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=[]
    )
    locations: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=["Paris"]
    )

    # Disponibilité
    availability_date: Mapped[date] = mapped_column(Date, nullable=True)
    internship_duration_months: Mapped[int] = mapped_column(Integer, default=6)

    # Liens
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # Seuils de l'agent
    min_relevance_score: Mapped[int] = mapped_column(Integer, default=60)
    auto_send_threshold: Mapped[int] = mapped_column(Integer, default=85)
    max_applications_per_day: Mapped[int] = mapped_column(Integer, default=5)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    user: Mapped["User"] = relationship(back_populates="profile")