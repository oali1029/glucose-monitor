from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, alerts as alert_engine
from app.schemas import ReadingCreate, ReadingResponse, ReadingOut, AlertOut

router = APIRouter()


@router.post("/readings", response_model=ReadingResponse, status_code=201)
def post_reading(payload: ReadingCreate, db: Session = Depends(get_db)):
    """Accept a CGM reading, persist it, run alert rules, and return results."""

    # Ensure the patient and device exist
    patient = crud.get_patient(db, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{payload.patient_id}' not found")

    device = crud.get_device(db, payload.device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{payload.device_id}' not found")

    # Persist reading
    reading = crud.create_reading(db, payload)

    # Update device heartbeat
    crud.update_device_status(db, payload.device_id, payload.battery_level, payload.signal_strength)

    # Run alert rules
    triggered = alert_engine.evaluate_reading_alerts(db, reading)

    # Audit log
    crud.create_audit_log(
        db,
        event_type="READING_RECEIVED",
        details={
            "reading_id": reading.id,
            "patient_id": reading.patient_id,
            "device_id": reading.device_id,
            "glucose_mg_dl": reading.glucose_mg_dl,
            "alerts_count": len(triggered),
        },
    )

    db.commit()
    db.refresh(reading)
    for a in triggered:
        db.refresh(a)

    return ReadingResponse(
        reading=ReadingOut.model_validate(reading),
        alerts_triggered=[AlertOut.model_validate(a) for a in triggered],
    )
