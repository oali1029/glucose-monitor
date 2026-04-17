"""Alert management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.schemas import AlertOut

router = APIRouter()


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    """Mark an alert as acknowledged."""
    alert = crud.acknowledge_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    crud.create_audit_log(
        db,
        event_type="ALERT_ACKNOWLEDGED",
        details={"alert_id": alert_id, "alert_type": alert.alert_type},
    )

    db.commit()
    db.refresh(alert)
    return AlertOut.model_validate(alert)
