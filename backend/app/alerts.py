from datetime import timedelta
from sqlalchemy.orm import Session

from app import crud, models


RAPID_CHANGE_THRESHOLD = 30   
RAPID_CHANGE_WINDOW_MIN = 10  


def evaluate_reading_alerts(
    db: Session,
    reading: models.Reading,
) -> list[models.Alert]:
    triggered: list[models.Alert] = []

    glucose = reading.glucose_mg_dl

    # Low Glucose alert
    if glucose < 70:
        alert = crud.create_alert(
            db=db,
            patient_id=reading.patient_id,
            device_id=reading.device_id,
            alert_type="LOW_GLUCOSE",
            severity="high",
            message=f"Low glucose detected: {glucose:.0f} mg/dL (threshold: <70 mg/dL). Immediate attention required.",
            reading_id=reading.id,
        )
        triggered.append(alert)

    # High Glucose alert
    elif glucose > 180:
        alert = crud.create_alert(
            db=db,
            patient_id=reading.patient_id,
            device_id=reading.device_id,
            alert_type="HIGH_GLUCOSE",
            severity="medium",
            message=f"High glucose detected: {glucose:.0f} mg/dL (threshold: >180 mg/dL). Monitor closely.",
            reading_id=reading.id,
        )
        triggered.append(alert)

    window_start = reading.timestamp - timedelta(minutes=RAPID_CHANGE_WINDOW_MIN)
    prev = crud.get_previous_reading(db, reading.patient_id, reading.timestamp)

    if prev:
        prev_ts = prev.timestamp
        win_ts  = window_start
        if prev_ts.tzinfo is None and win_ts.tzinfo is not None:
            win_ts = win_ts.replace(tzinfo=None)
        elif prev_ts.tzinfo is not None and win_ts.tzinfo is None:
            prev_ts = prev_ts.replace(tzinfo=None)

        if prev_ts >= win_ts:
            delta = glucose - prev.glucose_mg_dl

            if delta >= RAPID_CHANGE_THRESHOLD:
                alert = crud.create_alert(
                    db=db,
                    patient_id=reading.patient_id,
                    device_id=reading.device_id,
                    alert_type="RAPID_RISE",
                    severity="medium",
                    message=(
                        f"Rapid glucose rise: {prev.glucose_mg_dl:.0f} → {glucose:.0f} mg/dL "
                        f"(+{delta:.0f} mg/dL in <{RAPID_CHANGE_WINDOW_MIN} min)."
                    ),
                    reading_id=reading.id,
                )
                triggered.append(alert)

            elif delta <= -RAPID_CHANGE_THRESHOLD:
                alert = crud.create_alert(
                    db=db,
                    patient_id=reading.patient_id,
                    device_id=reading.device_id,
                    alert_type="RAPID_DROP",
                    severity="high",
                    message=(
                        f"Rapid glucose drop: {prev.glucose_mg_dl:.0f} → {glucose:.0f} mg/dL "
                        f"({delta:.0f} mg/dL in <{RAPID_CHANGE_WINDOW_MIN} min). Immediate attention required."
                    ),
                    reading_id=reading.id,
                )
                triggered.append(alert)

    return triggered


def evaluate_device_offline(
    db: Session,
    device: models.Device,
    offline_threshold_seconds: int = 15,
) -> models.Alert | None:
    """
    Check whether the device has gone silent.
    Creates a DEVICE_OFFLINE alert at most once per 30-second window to avoid duplicates.
    Returns the new Alert if one was created, otherwise None.
    """
    from datetime import datetime, timezone

    if device.last_seen_at is None:
        return None

    now = datetime.now(timezone.utc)
    last_seen = device.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    seconds_since = (now - last_seen).total_seconds()

    if seconds_since < offline_threshold_seconds:
        return None  

    if crud.has_recent_unacked_offline_alert(db, device.id, within_seconds=30):
        return None

    alert = crud.create_alert(
        db=db,
        patient_id=device.patient_id,
        device_id=device.id,
        alert_type="DEVICE_OFFLINE",
        severity="medium",
        message=(
            f"Device '{device.device_name}' has not reported in "
            f"{seconds_since:.0f} seconds. Sensor may be disconnected."
        ),
    )
    return alert
