import time
from datetime import datetime, timezone, timedelta

from tests.conftest import post_reading


class TestAlertRules:
    def test_low_glucose_alert(self, client):
        """A reading below 70 mg/dL must trigger a LOW_GLUCOSE alert."""
        resp = post_reading(client, glucose=55.0)
        assert resp.status_code == 201
        data = resp.json()
        types = [a["alert_type"] for a in data["alerts_triggered"]]
        assert "LOW_GLUCOSE" in types
        alert = next(a for a in data["alerts_triggered"] if a["alert_type"] == "LOW_GLUCOSE")
        assert alert["severity"] == "high"
        assert "55" in alert["message"]

    def test_high_glucose_alert(self, client):
        """A reading above 180 mg/dL must trigger a HIGH_GLUCOSE alert."""
        resp = post_reading(client, glucose=250.0)
        assert resp.status_code == 201
        data = resp.json()
        types = [a["alert_type"] for a in data["alerts_triggered"]]
        assert "HIGH_GLUCOSE" in types
        alert = next(a for a in data["alerts_triggered"] if a["alert_type"] == "HIGH_GLUCOSE")
        assert alert["severity"] == "medium"

    def test_normal_glucose_no_alert(self, client):
        """A reading in normal range should not trigger any glucose alerts."""
        resp = post_reading(client, glucose=110.0)
        assert resp.status_code == 201
        data = resp.json()
        assert data["alerts_triggered"] == []

    def test_rapid_rise_alert(self, client):
        """Two readings 30+ mg/dL apart within 10 minutes → RAPID_RISE."""
        now = datetime.now(timezone.utc)

        # First reading at T=0
        client.post("/readings", json={
            "patient_id": "patient-001",
            "device_id": "cgm-001",
            "timestamp": now.isoformat(),
            "glucose_mg_dl": 100.0,
            "battery_level": 80.0,
            "signal_strength": 90.0,
        })

        # Second reading 5 minutes later, +35 mg/dL
        resp = client.post("/readings", json={
            "patient_id": "patient-001",
            "device_id": "cgm-001",
            "timestamp": (now + timedelta(minutes=5)).isoformat(),
            "glucose_mg_dl": 135.0,
            "battery_level": 80.0,
            "signal_strength": 90.0,
        })
        assert resp.status_code == 201
        types = [a["alert_type"] for a in resp.json()["alerts_triggered"]]
        assert "RAPID_RISE" in types

    def test_rapid_drop_alert(self, client):
        """Two readings 30+ mg/dL drop within 10 minutes → RAPID_DROP."""
        now = datetime.now(timezone.utc)

        client.post("/readings", json={
            "patient_id": "patient-001",
            "device_id": "cgm-001",
            "timestamp": now.isoformat(),
            "glucose_mg_dl": 160.0,
            "battery_level": 80.0,
            "signal_strength": 90.0,
        })

        resp = client.post("/readings", json={
            "patient_id": "patient-001",
            "device_id": "cgm-001",
            "timestamp": (now + timedelta(minutes=5)).isoformat(),
            "glucose_mg_dl": 120.0,
            "battery_level": 80.0,
            "signal_strength": 90.0,
        })
        assert resp.status_code == 201
        types = [a["alert_type"] for a in resp.json()["alerts_triggered"]]
        assert "RAPID_DROP" in types
        alert = next(a for a in resp.json()["alerts_triggered"] if a["alert_type"] == "RAPID_DROP")
        assert alert["severity"] == "high"


class TestValidation:
    def test_invalid_payload_missing_fields(self, client):
        """Posting without required fields should return 422."""
        resp = client.post("/readings", json={"patient_id": "patient-001"})
        assert resp.status_code == 422

    def test_invalid_glucose_out_of_range(self, client):
        """Glucose value of 0 is invalid."""
        resp = post_reading(client, glucose=0.0)
        assert resp.status_code == 422

    def test_unknown_patient(self, client):
        """Posting for a non-existent patient should return 404."""
        resp = client.post("/readings", json={
            "patient_id": "ghost-patient",
            "device_id": "cgm-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "glucose_mg_dl": 100.0,
            "battery_level": 80.0,
            "signal_strength": 90.0,
        })
        assert resp.status_code == 404

class TestStorage:
    def test_posting_reading_stores_correctly(self, client):
        """A successfully posted reading should appear in /patients/{id}/readings."""
        post_reading(client, glucose=120.0)
        resp = client.get("/patients/patient-001/readings")
        assert resp.status_code == 200
        readings = resp.json()
        assert len(readings) >= 1
        assert readings[0]["glucose_mg_dl"] == 120.0

    def test_latest_reading_endpoint(self, client):
        """Latest endpoint returns the most recently posted reading."""
        post_reading(client, glucose=90.0)
        post_reading(client, glucose=95.0)
        resp = client.get("/patients/patient-001/latest")
        assert resp.status_code == 200
        assert resp.json()["glucose_mg_dl"] == 95.0

    def test_latest_reading_not_found(self, client):
        """Latest endpoint returns 404 when no readings exist for a patient."""
        resp = client.get("/patients/patient-001/latest")
        assert resp.status_code == 404

class TestAlertAcknowledgment:
    def test_acknowledge_alert(self, client):
        """Acknowledging an alert should set acknowledged=True."""
        resp = post_reading(client, glucose=55.0)
        alert_id = resp.json()["alerts_triggered"][0]["id"]

        ack_resp = client.post(f"/alerts/{alert_id}/acknowledge")
        assert ack_resp.status_code == 200
        assert ack_resp.json()["acknowledged"] is True

    def test_acknowledge_nonexistent_alert(self, client):
        """Acknowledging a non-existent alert should return 404."""
        resp = client.post("/alerts/nonexistent-id/acknowledge")
        assert resp.status_code == 404

class TestDeviceOffline:
    def test_device_online_after_reading(self, client):
        """Device should be online immediately after posting a reading."""
        post_reading(client, glucose=100.0)
        resp = client.get("/devices/cgm-001/status")
        assert resp.status_code == 200
        assert resp.json()["is_online"] is True

    def test_device_offline_detection(self, client):
     
        from tests.conftest import TestingSessionLocal
        from app import models as m
        from sqlalchemy import update

        db = TestingSessionLocal()
        try:
            stale_time = datetime.now(timezone.utc) - timedelta(seconds=30)
            db.execute(
                update(m.Device)
                .where(m.Device.id == "cgm-001")
                .values(last_seen_at=stale_time)
            )
            db.commit()
        finally:
            db.close()

        resp = client.get("/devices/cgm-001/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_online"] is False
