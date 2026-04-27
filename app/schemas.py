import uuid
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field

ALLOWED_SYMPTOMS = [
    "headache", "fatigue", "nausea", "dizziness", "chest pain",
    "shortness of breath", "back pain", "joint pain", "stomach pain",
    "fever", "cough", "rash", "insomnia", "loss of appetite",
    "anxiety", "palpitations",
]

ALLOWED_SPECIALTIES = [
    "General Physician", "Cardiologist", "Endocrinologist",
    "Neurologist", "Orthopedic", "Dermatologist", "Psychiatrist", "Other",
]


# --- Symptom Schemas ---

class SymptomCreate(BaseModel):
    date: date
    symptoms: List[str] = Field(..., min_length=1)
    severity: Optional[int] = Field(None, ge=1, le=10)
    mood: Optional[int] = Field(None, ge=1, le=10)
    energy: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=1000)


class SymptomUpdate(BaseModel):
    symptoms: Optional[List[str]] = Field(None, min_length=1)
    severity: Optional[int] = Field(None, ge=1, le=10)
    mood: Optional[int] = Field(None, ge=1, le=10)
    energy: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=1000)


class SymptomResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    symptoms: List[str]
    severity: Optional[int] = None
    mood: Optional[int] = None
    energy: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Visit Schemas ---

class VisitCreate(BaseModel):
    doctor_name: str = Field(..., min_length=1, max_length=100)
    specialty: Optional[str] = None
    visit_date: date
    reason: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription: Optional[str] = None
    follow_up: Optional[date] = None
    notes: Optional[str] = None


class VisitUpdate(BaseModel):
    doctor_name: Optional[str] = Field(None, min_length=1, max_length=100)
    specialty: Optional[str] = None
    visit_date: Optional[date] = None
    reason: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription: Optional[str] = None
    follow_up: Optional[date] = None
    notes: Optional[str] = None


class VisitResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    doctor_name: str
    specialty: Optional[str] = None
    visit_date: date
    reason: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription: Optional[str] = None
    follow_up: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
