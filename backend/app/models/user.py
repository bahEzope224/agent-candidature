# Modèle User mis à jour avec les champs Stripe
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Billing ──────────────────────────────────────────────────
    plan: Mapped[str] = mapped_column(String(20), default="free")
    # free | pro
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(50), nullable=True)
    # active | trialing | past_due | cancelled | cancelling

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)
    applications: Mapped[list["Application"]] = relationship(back_populates="user")
    job_offers: Mapped[list["JobOffer"]] = relationship(back_populates="user")
