import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Text
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

    # Identité
    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=True)

    # Formation
    education_level: Mapped[str] = mapped_column(String(100), nullable=True)
    school: Mapped[str] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=True)

    # Compétences
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    skills_technical: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    skills_soft: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    tools: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    strengths: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    # Cibles
    target_roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    target_locations: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    target_contract: Mapped[str] = mapped_column(String(100), nullable=True)
    min_salary: Mapped[int] = mapped_column(Integer, nullable=True)
    availability_date: Mapped[date] = mapped_column(Date, nullable=True)

    # Présentation
    pitch: Mapped[str] = mapped_column(Text, nullable=True)
    motivation: Mapped[str] = mapped_column(Text, nullable=True)

    # Liens
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relation
    user: Mapped["User"] = relationship(back_populates="profile")