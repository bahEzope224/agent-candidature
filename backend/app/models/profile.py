import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Infos personnelles
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    location = Column(String(200), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)

    # Formation
    education_level = Column(String(200), nullable=True)
    school = Column(String(200), nullable=True)
    graduation_year = Column(String(10), nullable=True)

    # Compétences (listes JSON)
    skills_technical = Column(JSON, default=list)   # ["Python", "SQL", ...]
    skills_soft = Column(JSON, default=list)         # ["Rigueur", ...]
    languages = Column(JSON, default=list)           # [{"lang": "Français", "level": "Natif"}]
    tools = Column(JSON, default=list)               # ["Power BI", "Tableau", ...]

    # Recherche
    target_roles = Column(JSON, default=list)        # ["Data Analyst", "Data Scientist"]
    target_locations = Column(JSON, default=list)    # ["Paris", "Remote"]
    target_contract = Column(String(50), default="stage")
    min_salary = Column(String(50), nullable=True)
    availability_date = Column(String(50), nullable=True)

    # Textes candidature
    pitch = Column(Text, nullable=True)              # "Étudiant en Master..."
    strengths = Column(Text, nullable=True)
    motivation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="profile")