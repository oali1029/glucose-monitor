# Real-Time Glucose Monitoring and Alert System

A portfolio-grade MVP that simulates a Continuous Glucose Monitor (CGM) device sending readings to a FastAPI backend, stores data in PostgreSQL, evaluates clinical alert rules, and presents a live dashboard.

---

## Architecture

```
┌──────────────┐        POST /readings        ┌───────────────────┐
│  Simulator   │ ─────────────────────────▶   │   FastAPI Backend  │
│  (Python)    │   every 5 seconds             │   (Python)         │
└──────────────┘                               └─────────┬─────────┘
                                                         │ SQLAlchemy ORM
                                                         ▼
                                               ┌───────────────────┐
                                               │   PostgreSQL DB    │
                                               └───────────────────┘
                                                         ▲
┌──────────────┐        GET /dashboard/summary           │
│  Browser     │ ─────────────────────────▶   FastAPI reads & returns
│  (Dashboard) │   poll every 5 seconds
└──────────────┘
```

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2 + Pydantic v2 |
| Testing | pytest + TestClient (SQLite in-memory) |
| Frontend | HTML / CSS / JavaScript, Chart.js |
| Containers | Docker + Docker Compose |

---

## Quick Start

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Port `3000` (frontend), `8000` (backend), `5432` (postgres) must be free

### 1. Clone / unzip the project

```bash
cd glucose-monitor
```

### 2. Start everything

```bash
docker compose up --build
```

This will:
1. Start PostgreSQL and wait for it to be healthy
2. Start the FastAPI backend (tables are created + seed data inserted on startup)
3. Start the CGM simulator (waits for the backend, then sends a reading every 5 seconds)
4. Start the nginx frontend

### 3. Open the dashboard

```
http://localhost:3000
```

### 4. Explore the API

Interactive docs (Swagger UI):
```
http://localhost:8000/docs
```

---

## Running Tests

Tests use an in-memory SQLite database — no running Postgres required.

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/readings` | Submit a CGM reading |
| `GET` | `/patients/{id}/latest` | Latest reading for a patient |
| `GET` | `/patients/{id}/readings` | Recent readings (newest first) |
| `GET` | `/patients/{id}/alerts` | Recent alerts |
| `POST` | `/alerts/{id}/acknowledge` | Acknowledge an alert |
| `GET` | `/devices/{id}/status` | Device online/offline status |
| `GET` | `/dashboard/summary` | Aggregate payload for the UI |
| `GET` | `/health` | Health check |

---

## Alert Rules

| Rule | Condition | Severity |
|---|---|---|
| `LOW_GLUCOSE` | glucose < 70 mg/dL | **high** |
| `HIGH_GLUCOSE` | glucose > 180 mg/dL | medium |
| `RAPID_RISE` | +30 mg/dL within 10 minutes | medium |
| `RAPID_DROP` | −30 mg/dL within 10 minutes | **high** |
| `DEVICE_OFFLINE` | no reading for > 15 seconds | medium |

Duplicate `DEVICE_OFFLINE` alerts are suppressed: at most one is created per 30-second window.

---

## Database Schema

```
patients       (id, name)
devices        (id, patient_id, device_name, last_seen_at, battery_level, signal_strength)
readings       (id, patient_id, device_id, timestamp, glucose_mg_dl)
alerts         (id, patient_id, device_id, reading_id?, alert_type, severity, message, created_at, acknowledged)
audit_logs     (id, event_type, details, created_at)
```

---

## Seed Data

| Field | Value |
|---|---|
| Patient ID | `patient-001` |
| Patient name | Demo Patient |
| Device ID | `cgm-001` |
| Device name | Demo CGM Sensor |

---

## Project Structure

```
glucose-monitor/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, startup, CORS
│   │   ├── database.py      # SQLAlchemy engine & session
│   │   ├── models.py        # ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── crud.py          # Database operations
│   │   ├── alerts.py        # Alert evaluation engine
│   │   └── routers/
│   │       ├── readings.py
│   │       ├── patients.py
│   │       ├── alerts.py
│   │       ├── devices.py
│   │       └── dashboard.py
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── simulator/
│   ├── simulator.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Stopping the System

```bash
docker compose down          # stop containers (keep data)
docker compose down -v       # stop + delete database volume
```
