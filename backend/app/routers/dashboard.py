from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, alerts as alert_engine
from app.schemas import (
    DashboardSummary, PatientOut, ReadingOut, AlertOut, DeviceStatusOut
)

router = APIRouter()

PATIENT_ID = "patient-001"
DEVICE_ID = "cgm-001"
OFFLINE_THRESHOLD_SECONDS = 15


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    patient = crud.get_patient(db, PATIENT_ID)
    device = crud.get_device(db, DEVICE_ID)

    device_status = None
    if device:
        is_online = False
        if device.last_seen_at:
            last_seen = device.last_seen_at
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
            is_online = elapsed <= OFFLINE_THRESHOLD_SECONDS

            if not is_online:
                offline_alert = alert_engine.evaluate_device_offline(
                    db, device, OFFLINE_THRESHOLD_SECONDS
                )
                if offline_alert:
                    db.commit()

        device_status = DeviceStatusOut(
            id=device.id,
            patient_id=device.patient_id,
            device_name=device.device_name,
            last_seen_at=device.last_seen_at,
            is_online=is_online,
            battery_level=device.battery_level,
            signal_strength=device.signal_strength,
        )

    latest_reading_obj = crud.get_latest_reading(db, PATIENT_ID) if patient else None
    recent_readings = crud.get_recent_readings(db, PATIENT_ID, limit=50) if patient else []
    recent_alerts = crud.get_recent_alerts(db, PATIENT_ID, limit=20) if patient else []

    return DashboardSummary(
        patient=PatientOut.model_validate(patient) if patient else PatientOut(id="", name="Unknown"),
        latest_reading=ReadingOut.model_validate(latest_reading_obj) if latest_reading_obj else None,
        recent_readings=[ReadingOut.model_validate(r) for r in recent_readings],
        recent_alerts=[AlertOut.model_validate(a) for a in recent_alerts],
        device_status=device_status,
    )
