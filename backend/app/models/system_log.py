from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.database import Base
from datetime import datetime
import uuid

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    level = Column(String(50), nullable=False) # INFO, WARNING, ERROR, FATAL
    action = Column(String(100), nullable=False) # ex: LOGIN_FAILED, SCRAPE_ERROR, UNHANDLED_EXCEPTION
    details = Column(JSON, nullable=True) # Pour stocker la stacktrace, la requête HTTP, l'IP, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
