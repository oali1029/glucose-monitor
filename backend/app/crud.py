"""CRUD operations — thin wrappers around SQLAlchemy queries."""

import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app import models
from app.schemas import ReadingCreate


def create_reading(db: Session, data: ReadingCreate) -> models.Reading:
    reading = models.Reading(
        id=str(uuid.uuid4()),
        patient_id=data.patient_id,
        device_id=data.device_id,
        timestamp=data.timestamp,
        glucose_mg_dl=data.glucose_mg_dl,
    )
    db.add(reading)
    db.flush()  
    return reading


def get_latest_reading(db: Session, patient_id: str) -> models.Reading | None:
    return (
        db.query(models.Reading)
        .filter(models.Reading.patient_id == patient_id)
        .order_by(desc(models.Reading.timestamp))
        .first()
    )


def get_recent_readings(db: Session, patient_id: str, limit: int = 50) -> list[models.Reading]:
    return (
        db.query(models.Reading)
        .filter(models.Reading.patient_id == patient_id)
        .order_by(desc(models.Reading.timestamp))
        .limit(limit)
        .all()
    )


def get_previous_reading(db: Session, patient_id: str, before_timestamp: datetime) -> models.Reading | None:
    before_ts = before_timestamp.replace(tzinfo=None) if before_timestamp.tzinfo else before_timestamp
    return (
        db.query(models.Reading)
        .filter(
            models.Reading.patient_id == patient_id,
            models.Reading.timestamp < before_ts,
        )
        .order_by(desc(models.Reading.timestamp))
        .first()
    )


def get_device(db: Session, device_id: str) -> models.Device | None:
    return db.query(models.Device).filter(models.Device.id == device_id).first()


def update_device_status(db: Session, device_id: str, battery_level: float, signal_strength: float):
    device = get_device(db, device_id)
    if device:
        device.last_seen_at = datetime.now(timezone.utc)
        device.battery_level = battery_level
        device.signal_strength = signal_strength
        db.flush()
    return device


def create_alert(
    db: Session,
    patient_id: str,
    device_id: str,
    alert_type: str,
    severity: str,
    message: str,
    reading_id: str | None = None,
) -> models.Alert:
    alert = models.Alert(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        device_id=device_id,
        reading_id=reading_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        acknowledged=False,
    )
    db.add(alert)
    db.flush()
    return alert


def get_recent_alerts(db: Session, patient_id: str, limit: int = 20) -> list[models.Alert]:
    return (
        db.query(models.Alert)
        .filter(models.Alert.patient_id == patient_id)
        .order_by(desc(models.Alert.created_at))
        .limit(limit)
        .all()
    )


def acknowledge_alert(db: Session, alert_id: str) -> models.Alert | None:
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if alert:
        alert.acknowledged = True
        db.flush()
    return alert


def has_recent_unacked_offline_alert(db: Session, device_id: str, within_seconds: int = 30) -> bool:
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
    count = (
        db.query(models.Alert)
        .filter(
            models.Alert.device_id == device_id,
            models.Alert.alert_type == "DEVICE_OFFLINE",
            models.Alert.acknowledged == False,
            models.Alert.created_at >= cutoff,
        )
        .count()
    )
    return count > 0

def get_patient(db: Session, patient_id: str) -> models.Patient | None:
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()


def create_audit_log(db: Session, event_type: str, details: dict | None = None):
    log = models.AuditLog(
        id=str(uuid.uuid4()),
        event_type=event_type,
        details=json.dumps(details) if details else None,
    )
    db.add(log)
    db.flush()
    return log
