import os
import time
import random
import logging
from datetime import datetime, timezone

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SIM] %(message)s")
log = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
PATIENT_ID  = os.getenv("PATIENT_ID",  "patient-001")
DEVICE_ID   = os.getenv("DEVICE_ID",   "cgm-001")
INTERVAL    = float(os.getenv("INTERVAL", "5")) 
READINGS_URL = f"{BACKEND_URL}/readings"


current_glucose: float = random.uniform(90, 130)
battery_level:   float = 95.0
signal_strength: float = 90.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def next_glucose(previous: float) -> tuple[float, str]:
    """
    Return (new_glucose, scenario_label).
    Most readings drift ±5 mg/dL from the previous value.
    """
    roll = random.random()

    if roll < 0.05:
        # Low glucose event
        value = random.uniform(45, 69)
        return value, "LOW"

    if roll < 0.10:
        # High glucose event
        value = random.uniform(181, 280)
        return value, "HIGH"

    if roll < 0.15:
        # Rapid rise — add 35–50 mg/dL to the last reading
        value = _clamp(previous + random.uniform(35, 50), 80, 400)
        return value, "RAPID_RISE"

    if roll < 0.20:
        # Rapid drop — subtract 35–50 mg/dL from the last reading
        value = _clamp(previous - random.uniform(35, 50), 40, 300)
        return value, "RAPID_DROP"

    # Normal drift
    drift = random.gauss(0, 5)  # mean 0, std 5 mg/dL
    value = _clamp(previous + drift, 70, 170)
    return value, "NORMAL"


def simulate_battery():
    """Slowly discharge; jitter to look realistic."""
    global battery_level
    battery_level = _clamp(battery_level - random.uniform(0, 0.3), 0, 100)
    return battery_level


def simulate_signal():
    """Signal fluctuates between 70–100 %."""
    global signal_strength
    signal_strength = _clamp(signal_strength + random.gauss(0, 3), 60, 100)
    return signal_strength


def wait_for_backend(retries: int = 30, delay: float = 2.0):
    """Block until the backend health check responds."""
    log.info("Waiting for backend at %s …", BACKEND_URL)
    for attempt in range(retries):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                log.info("Backend is ready.")
                return
        except requests.RequestException:
            pass
        log.info("Backend not ready yet (%d/%d). Retrying in %.0fs …", attempt + 1, retries, delay)
        time.sleep(delay)
    raise RuntimeError("Backend did not become ready in time.")


def main():
    global current_glucose
    wait_for_backend()

    reading_count = 0
    log.info(
        "Simulator started → patient=%s  device=%s  interval=%.0fs",
        PATIENT_ID, DEVICE_ID, INTERVAL,
    )

    while True:
        reading_count += 1
        glucose, scenario = next_glucose(current_glucose)

        # Sensor dropout — skip this cycle entirely
        if random.random() < 0.03:
            log.warning("[%d] Sensor dropout — skipping reading.", reading_count)
            time.sleep(INTERVAL)
            continue

        current_glucose = glucose
        battery  = simulate_battery()
        signal   = simulate_signal()
        ts       = datetime.now(timezone.utc).isoformat()

        payload = {
            "patient_id":     PATIENT_ID,
            "device_id":      DEVICE_ID,
            "timestamp":      ts,
            "glucose_mg_dl":  round(glucose, 1),
            "battery_level":  round(battery, 1),
            "signal_strength": round(signal, 1),
        }

        try:
            resp = requests.post(READINGS_URL, json=payload, timeout=5)
            if resp.status_code == 201:
                alerts = resp.json().get("alerts_triggered", [])
                alert_str = ", ".join(a["alert_type"] for a in alerts) or "—"
                log.info(
                    "[%d] %s | glucose=%.0f mg/dL | bat=%.0f%% | sig=%.0f%% | alerts: %s",
                    reading_count, scenario, glucose, battery, signal, alert_str,
                )
            else:
                log.error("[%d] Backend error %d: %s", reading_count, resp.status_code, resp.text)

        except requests.RequestException as exc:
            log.error("[%d] Failed to POST reading: %s", reading_count, exc)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
