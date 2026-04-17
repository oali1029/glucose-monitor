from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.schemas import ReadingOut, AlertOut

router = APIRouter()


@router.get("/patients/{patient_id}/latest", response_model=ReadingOut)
def get_latest_reading(patient_id: str, db: Session = Depends(get_db)):
    """Return the most recent glucose reading for a patient."""
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    reading = crud.get_latest_reading(db, patient_id)
    if not reading:
        raise HTTPException(status_code=404, detail="No readings found for this patient")
    return ReadingOut.model_validate(reading)


@router.get("/patients/{patient_id}/readings", response_model=list[ReadingOut])
def get_readings(
    patient_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return recent glucose readings for a patient, newest first."""
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    readings = crud.get_recent_readings(db, patient_id, limit)
    return [ReadingOut.model_validate(r) for r in readings]


@router.get("/patients/{patient_id}/alerts", response_model=list[AlertOut])
def get_alerts(
    patient_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return recent alerts for a patient, newest first."""
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    alert_list = crud.get_recent_alerts(db, patient_id, limit)
    return [AlertOut.model_validate(a) for a in alert_list]
