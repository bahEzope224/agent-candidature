from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    job_offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_offers.id")
    )

    # Contenu de la candidature
    email_subject: Mapped[str] = mapped_column(String(500), nullable=True)
    email_body: Mapped[str] = mapped_column(Text, nullable=True)
    cover_letter_text: Mapped[str] = mapped_column(Text, nullable=True)

    # Statut (cycle de vie manuel)
    status: Mapped[str] = mapped_column(String(100), default="to_apply")
    # to_apply         → lettre générée, en attente de candidature manuelle
    # sent             → l'utilisateur confirme avoir candidaté
    # follow_up_needed → J+7 après "sent" → relance à envoyer
    # follow_up_sent   → l'utilisateur confirme avoir relancé
    # no_response      → J+7 après "follow_up_sent"
    # interview        → entretien obtenu (manuel)
    # refused          → refus (manuel)
    # archived         → archivé

    # Métadonnées d'envoi (renseignées manuellement)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    followup_sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    followup_generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    followup_email_body: Mapped[str] = mapped_column(Text, nullable=True)
    send_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # LLM
    llm_confidence_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Validation humaine
    requires_human_validation: Mapped[bool] = mapped_column(Boolean, default=False)
    human_validated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Gmail thread
    gmail_thread_id: Mapped[str] = mapped_column(String(255), nullable=True)
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=True)

    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relations
    user: Mapped["User"] = relationship(back_populates="applications")
    job_offer: Mapped["JobOffer"] = relationship(back_populates="applications")
    email_threads: Mapped[list["EmailThread"]] = relationship(back_populates="application")
    followups: Mapped[list["Followup"]] = relationship(back_populates="application")
