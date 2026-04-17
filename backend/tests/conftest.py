import pytest
import app.database as _db_module  
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine_test = create_engine(
    SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

_db_module.engine = engine_test
_db_module.SessionLocal = TestingSessionLocal

from app.main import app  
from app.database import Base, get_db  
from app import models  


from fastapi.testclient import TestClient


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine_test)

    # Seed patient and device
    db = TestingSessionLocal()
    try:
        if not db.query(models.Patient).filter_by(id="patient-001").first():
            db.add(models.Patient(id="patient-001", name="Demo Patient"))
        if not db.query(models.Device).filter_by(id="cgm-001").first():
            db.add(
                models.Device(
                    id="cgm-001",
                    patient_id="patient-001",
                    device_name="Demo CGM Sensor",
                )
            )
        db.commit()
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def post_reading(client, glucose: float, battery: float = 80.0, signal: float = 90.0):
    """Helper to POST a reading with the given glucose value."""
    from datetime import datetime, timezone
    return client.post("/readings", json={
        "patient_id": "patient-001",
        "device_id": "cgm-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "glucose_mg_dl": glucose,
        "battery_level": battery,
        "signal_strength": signal,
    })
