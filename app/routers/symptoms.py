import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SymptomLog
from app.schemas import SymptomCreate, SymptomUpdate, ALLOWED_SYMPTOMS
from app.utils.auth import get_current_user_id
from app.cache import (
    cache_get, cache_set, cache_delete_pattern,
    key_symptoms, key_trends, pattern_health, pattern_ai,
    TTL_SYMPTOMS, TTL_TRENDS,
)

router = APIRouter(prefix="/api/symptoms", tags=["Symptoms"])


def symptom_to_dict(log: SymptomLog) -> dict:
    return {
        "id": str(log.id),
        "user_id": str(log.user_id),
        "date": log.date.isoformat(),
        "symptoms": log.symptoms,
        "severity": log.severity,
        "mood": log.mood,
        "energy": log.energy,
        "notes": log.notes,
        "created_at": log.created_at.isoformat(),
    }


def validate_symptoms(symptoms: list):
    for s in symptoms:
        if s not in ALLOWED_SYMPTOMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": f"Invalid symptom: {s}. Allowed: {', '.join(ALLOWED_SYMPTOMS)}"},
            )


@router.get("")
async def get_symptoms(
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cache_key = key_symptoms(user_id, days)
    cached = await cache_get(cache_key)
    if cached is not None:
        return {"success": True, "data": cached}

    start_date = date.today() - timedelta(days=days)
    logs = (
        db.query(SymptomLog)
        .filter(
            SymptomLog.user_id == uuid.UUID(user_id),
            SymptomLog.date >= start_date,
        )
        .order_by(SymptomLog.date.desc())
        .all()
    )
    result = [symptom_to_dict(l) for l in logs]
    await cache_set(cache_key, result, TTL_SYMPTOMS)
    return {"success": True, "data": result}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_symptom(
    body: SymptomCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    validate_symptoms(body.symptoms)

    uid = uuid.UUID(user_id)
    existing = (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == uid, SymptomLog.date == body.date)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "A symptom log already exists for this date"},
        )

    log = SymptomLog(
        user_id=uid,
        date=body.date,
        symptoms=body.symptoms,
        severity=body.severity,
        mood=body.mood,
        energy=body.energy,
        notes=body.notes,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    await cache_delete_pattern(pattern_health(user_id))
    await cache_delete_pattern(pattern_ai(user_id))

    return {"success": True, "data": symptom_to_dict(log)}


@router.get("/today")
async def get_today_symptom(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    today = date.today()
    log = (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == uuid.UUID(user_id), SymptomLog.date == today)
        .first()
    )
    if not log:
        return {"success": True, "data": None}
    return {"success": True, "data": symptom_to_dict(log)}


@router.get("/trends")
async def get_trends(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cache_key = key_trends(user_id)
    cached = await cache_get(cache_key)
    if cached is not None:
        return {"success": True, "data": cached}

    start_date = date.today() - timedelta(days=14)
    logs = (
        db.query(SymptomLog)
        .filter(
            SymptomLog.user_id == uuid.UUID(user_id),
            SymptomLog.date >= start_date,
        )
        .order_by(SymptomLog.date.asc())
        .all()
    )

    result = []
    for log in logs:
        result.append({
            "date": log.date.isoformat(),
            "avg_mood": log.mood if log.mood else None,
            "avg_energy": log.energy if log.energy else None,
            "avg_severity": log.severity if log.severity else None,
            "symptom_count": len(log.symptoms) if log.symptoms else 0,
        })

    await cache_set(cache_key, result, TTL_TRENDS)
    return {"success": True, "data": result}


@router.get("/{symptom_id}")
async def get_symptom(
    symptom_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        sid = uuid.UUID(symptom_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"success": False, "message": "Invalid symptom log ID"})

    log = (
        db.query(SymptomLog)
        .filter(SymptomLog.id == sid, SymptomLog.user_id == uuid.UUID(user_id))
        .first()
    )
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Symptom log not found"},
        )
    return {"success": True, "data": symptom_to_dict(log)}


@router.put("/{symptom_id}")
async def update_symptom(
    symptom_id: str,
    body: SymptomUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        sid = uuid.UUID(symptom_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"success": False, "message": "Invalid symptom log ID"})

    log = (
        db.query(SymptomLog)
        .filter(SymptomLog.id == sid, SymptomLog.user_id == uuid.UUID(user_id))
        .first()
    )
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Symptom log not found"},
        )

    update_data = body.model_dump(exclude_unset=True)
    if "symptoms" in update_data:
        validate_symptoms(update_data["symptoms"])

    for field, value in update_data.items():
        setattr(log, field, value)

    db.commit()
    db.refresh(log)

    await cache_delete_pattern(pattern_health(user_id))
    await cache_delete_pattern(pattern_ai(user_id))

    return {"success": True, "data": symptom_to_dict(log)}


@router.delete("/{symptom_id}")
async def delete_symptom(
    symptom_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        sid = uuid.UUID(symptom_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"success": False, "message": "Invalid symptom log ID"})

    log = (
        db.query(SymptomLog)
        .filter(SymptomLog.id == sid, SymptomLog.user_id == uuid.UUID(user_id))
        .first()
    )
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Symptom log not found"},
        )

    db.delete(log)
    db.commit()

    await cache_delete_pattern(pattern_health(user_id))
    await cache_delete_pattern(pattern_ai(user_id))

    return {"success": True, "message": "Symptom log deleted successfully"}
