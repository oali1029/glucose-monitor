from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, alerts as alert_engine
from app.schemas import DeviceStatusOut

router = APIRouter()

# A device is considered offline if no reading in this many seconds
OFFLINE_THRESHOLD_SECONDS = 15


@router.get("/devices/{device_id}/status", response_model=DeviceStatusOut)
def get_device_status(device_id: str, db: Session = Depends(get_db)):
    """Return device health: online/offline, battery, signal strength."""
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

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

    return DeviceStatusOut(
        id=device.id,
        patient_id=device.patient_id,
        device_name=device.device_name,
        last_seen_at=device.last_seen_at,
        is_online=is_online,
        battery_level=device.battery_level,
        signal_strength=device.signal_strength,
    )
