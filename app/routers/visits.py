import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DoctorVisit
from app.schemas import VisitCreate, VisitUpdate, ALLOWED_SPECIALTIES
from app.utils.auth import get_current_user_id
from app.cache import (
    cache_get, cache_set, cache_delete,
    key_visits, key_upcoming, pattern_ai,
    TTL_VISITS,
)

router = APIRouter(prefix="/api/visits", tags=["Doctor Visits"])


def visit_to_dict(visit: DoctorVisit) -> dict:
    return {
        "id": str(visit.id),
        "user_id": str(visit.user_id),
        "doctor_name": visit.doctor_name,
        "specialty": visit.specialty,
        "visit_date": visit.visit_date.isoformat(),
        "reason": visit.reason,
        "diagnosis": visit.diagnosis,
        "prescription": visit.prescription,
        "follow_up": visit.follow_up.isoformat() if visit.follow_up else None,
        "notes": visit.notes,
        "created_at": visit.created_at.isoformat(),
    }


def validate_specialty(specialty: Optional[str]):
    if specialty is not None and specialty not in ALLOWED_SPECIALTIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": f"Invalid specialty. Allowed: {', '.join(ALLOWED_SPECIALTIES)}"},
        )


async def invalidate_visit_caches(user_id: str):
    await cache_delete(key_visits(user_id))
    await cache_delete(key_upcoming(user_id))
    from app.cache import cache_delete_pattern
    await cache_delete_pattern(pattern_ai(user_id))


@router.get("")
async def get_visits(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cache_key = key_visits(user_id)
    cached = await cache_get(cache_key)
    if cached is not None:
        return {"success": True, "data": cached}

    visits = (
        db.query(DoctorVisit)
        .filter(DoctorVisit.user_id == uuid.UUID(user_id))
        .order_by(DoctorVisit.visit_date.desc())
        .all()
    )
    result = [visit_to_dict(v) for v in visits]
    await cache_set(cache_key, result, TTL_VISITS)
    return {"success": True, "data": result}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_visit(
    body: VisitCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    validate_specialty(body.specialty)

    visit = DoctorVisit(
        user_id=uuid.UUID(user_id),
        doctor_name=body.doctor_name,
        specialty=body.specialty,
        visit_date=body.visit_date,
        reason=body.reason,
        diagnosis=body.diagnosis,
        prescription=body.prescription,
        follow_up=body.follow_up,
        notes=body.notes,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)

    await invalidate_visit_caches(user_id)

    return {"success": True, "data": visit_to_dict(visit)}


@router.get("/upcoming")
async def get_upcoming_visits(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cache_key = key_upcoming(user_id)
    cached = await cache_get(cache_key)
    if cached is not None:
        return {"success": True, "data": cached}

    today = date.today()
    visits = (
        db.query(DoctorVisit)
        .filter(
            DoctorVisit.user_id == uuid.UUID(user_id),
            DoctorVisit.follow_up != None,
            DoctorVisit.follow_up >= today,
        )
        .order_by(DoctorVisit.follow_up.asc())
        .all()
    )
    result = [visit_to_dict(v) for v in visits]
    await cache_set(cache_key, result, TTL_VISITS)
    return {"success": True, "data": result}


@router.get("/{visit_id}")
async def get_visit(
    visit_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        vid = uuid.UUID(visit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"success": False, "message": "Invalid visit ID"})

    visit = (
        db.query(DoctorVisit)
        .filter(DoctorVisit.id == vid, DoctorVisit.user_id == uuid.UUID(user_id))
        .first()
    )
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Visit not found"},
        )
    return {"success": True, "data": visit_to_dict(visit)}


@router.put("/{visit_id}")
async def update_visit(
    visit_id: str,
    body: VisitUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        vid = uuid.UUID(visit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"success": False, "message": "Invalid visit ID"})

    visit = (
        db.query(DoctorVisit)
        .filter(DoctorVisit.id == vid, DoctorVisit.user_id == uuid.UUID(user_id))
        .first()
    )
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Visit not found"},
        )

    update_data = body.model_dump(exclude_unset=True)
    if "specialty" in update_data:
        validate_specialty(update_data["specialty"])

    for field, value in update_data.items():
        setattr(visit, field, value)

    db.commit()
    db.refresh(visit)

    await invalidate_visit_caches(user_id)

    return {"success": True, "data": visit_to_dict(visit)}


@router.delete("/{visit_id}")
async def delete_visit(
    visit_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        vid = uuid.UUID(visit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"success": False, "message": "Invalid visit ID"})

    visit = (
        db.query(DoctorVisit)
        .filter(DoctorVisit.id == vid, DoctorVisit.user_id == uuid.UUID(user_id))
        .first()
    )
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "Visit not found"},
        )

    db.delete(visit)
    db.commit()

    await invalidate_visit_caches(user_id)

    return {"success": True, "message": "Visit deleted successfully"}
