import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Date, Text, DateTime, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.database import Base


class SymptomLog(Base):
    __tablename__ = "symptom_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    date = Column(Date, nullable=False)
    symptoms = Column(ARRAY(Text), nullable=False)
    severity = Column(Integer, nullable=True)
    mood = Column(Integer, nullable=True)
    energy = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_symptom_log_user_date"),
        CheckConstraint("severity IS NULL OR (severity >= 1 AND severity <= 10)", name="ck_severity_range"),
        CheckConstraint("mood IS NULL OR (mood >= 1 AND mood <= 10)", name="ck_mood_range"),
        CheckConstraint("energy IS NULL OR (energy >= 1 AND energy <= 10)", name="ck_energy_range"),
    )


class DoctorVisit(Base):
    __tablename__ = "doctor_visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    doctor_name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=True)
    visit_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    prescription = Column(Text, nullable=True)
    follow_up = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
