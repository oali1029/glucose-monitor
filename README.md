# Real-Time Glucose Monitoring and Alert System

This project is a healthcare-focused simulation of a continuous glucose monitoring (CGM) system. It models how device data is ingested, validated, stored, and analyzed in real time, with alert generation and a simple dashboard for visualization.

The system includes a simulated CGM device that streams glucose readings to a FastAPI backend. The backend processes incoming data, evaluates alert conditions, tracks device health, and exposes APIs for retrieving patient data and alerts. A lightweight dashboard displays recent readings and system status.

## Key Features

- Real-time glucose data simulation
- Alert engine for low and high glucose levels and rapid changes
- Device health monitoring including online and offline status
- REST API built with FastAPI
- PostgreSQL database for persistent storage
- Simple web dashboard for visualization
- Dockerized multi-service architecture
- Automated tests for API endpoints and alert logic

## System Architecture

The system consists of three main components:

- Backend: FastAPI service responsible for data ingestion, processing, and API endpoints
- Simulator: Python service that generates and sends glucose readings
- Frontend: Static dashboard served via nginx
- Database: PostgreSQL instance for storing readings, alerts, and device data

## Tech Stack

Backend: Python 3.12, FastAPI, Uvicorn  
Database: PostgreSQL 16  
ORM: SQLAlchemy 2, Pydantic v2  
Testing: pytest, FastAPI TestClient, SQLite for local test isolation  
Frontend: Single-page dashboard using HTML with inline CSS and JavaScript, Chart.js  
Containers: Docker, Docker Compose  

## Project Structure

glucose-monitor/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── alerts.py
│   │   └── routers/
│   ├── tests/
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

## Getting Started

### Prerequisites

- Docker Desktop installed and running

### Run the system

docker compose up --build

### Services

- Backend API: http://localhost:8000
- Frontend Dashboard: http://localhost:8080

## API Overview

POST /readings  
Accepts glucose readings from the simulator, stores data, and evaluates alerts

GET /patients/{patient_id}/latest  
Returns the most recent glucose reading

GET /patients/{patient_id}/readings  
Returns recent readings for a patient

GET /patients/{patient_id}/alerts  
Returns recent alerts

GET /devices/{device_id}/status  
Returns device health and last seen time

GET /dashboard/summary  
Returns aggregated data for the dashboard

## Testing

Run tests with:

pytest

Tests use a local SQLite database, so no running PostgreSQL instance is required.

## Notes

- This project is a simulation intended for demonstration and learning purposes
- The system models real-time ingestion and alert processing but is not a clinical system
- The dashboard is designed for a single demo patient and device
