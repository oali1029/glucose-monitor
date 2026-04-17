from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ReadingCreate(BaseModel):
    patient_id: str = Field(..., min_length=1)
    device_id: str = Field(..., min_length=1)
    timestamp: datetime
    glucose_mg_dl: float = Field(..., gt=0, lt=1000)
    battery_level: float = Field(..., ge=0, le=100)
    signal_strength: float = Field(..., ge=0, le=100)

    @field_validator("glucose_mg_dl")
    @classmethod
    def glucose_must_be_realistic(cls, v: float) -> float:
        if v < 20 or v > 600:
            raise ValueError("glucose_mg_dl must be between 20 and 600")
        return v

class ReadingOut(BaseModel):
    id: str
    patient_id: str
    device_id: str
    timestamp: datetime
    glucose_mg_dl: float

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: str
    patient_id: str
    device_id: str
    reading_id: Optional[str]
    alert_type: str
    severity: str
    message: str
    created_at: datetime
    acknowledged: bool

    model_config = {"from_attributes": True}


class DeviceStatusOut(BaseModel):
    id: str
    patient_id: str
    device_name: str
    last_seen_at: Optional[datetime]
    is_online: bool
    battery_level: Optional[float]
    signal_strength: Optional[float]

    model_config = {"from_attributes": True}


class PatientOut(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class ReadingResponse(BaseModel):
    reading: ReadingOut
    alerts_triggered: list[AlertOut]


class DashboardSummary(BaseModel):
    patient: PatientOut
    latest_reading: Optional[ReadingOut]
    recent_readings: list[ReadingOut]
    recent_alerts: list[AlertOut]
    device_status: Optional[DeviceStatusOut]
