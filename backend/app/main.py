
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, SessionLocal, Base
from app import models 
from app.routers import readings, patients, alerts, devices, dashboard


def seed_database():
    db = SessionLocal()
    try:
        # Patient
        if not db.query(models.Patient).filter_by(id="patient-001").first():
            db.add(models.Patient(id="patient-001", name="Demo Patient"))

        # Device
        if not db.query(models.Device).filter_by(id="cgm-001").first():
            db.add(
                models.Device(
                    id="cgm-001",
                    patient_id="patient-001",
                    device_name="Demo CGM Sensor",
                )
            )

        db.commit()
        print("Seed data verified.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(
    title="Real-Time Glucose Monitoring API",
    description="Backend for a continuous glucose monitor (CGM) demo system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#Routers
app.include_router(readings.router)
app.include_router(patients.router)
app.include_router(alerts.router)
app.include_router(devices.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
