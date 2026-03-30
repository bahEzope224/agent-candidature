from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.user import User

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Identité
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)

    # Formation
    education_level: Mapped[str] = mapped_column(String, nullable=True)
    school: Mapped[str] = mapped_column(String, nullable=True)
    graduation_year: Mapped[str] = mapped_column(String, nullable=True)

    # Compétences — types exacts de la base
    skills: Mapped[list] = mapped_column(JSON, default=[])
    skills_technical: Mapped[list] = mapped_column(JSON, default=[])
    skills_soft: Mapped[list] = mapped_column(JSON, default=[])
    tools: Mapped[list] = mapped_column(JSON, default=[])
    languages: Mapped[list] = mapped_column(JSON, default=[])
    strengths: Mapped[str] = mapped_column(Text, nullable=True)

    # Cibles
    target_roles: Mapped[list] = mapped_column(JSON, default=[])
    target_locations: Mapped[list] = mapped_column(JSON, default=[])
    target_contract: Mapped[str] = mapped_column(String, nullable=True)
    min_salary: Mapped[str] = mapped_column(String, nullable=True)
    availability_date: Mapped[str] = mapped_column(String, nullable=True)

    # Présentation
    pitch: Mapped[str] = mapped_column(Text, nullable=True)
    motivation: Mapped[str] = mapped_column(Text, nullable=True)

    # Liens
    linkedin_url: Mapped[str] = mapped_column(String, nullable=True)
    portfolio_url: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relation
    user: Mapped["User"] = relationship(back_populates="profile")