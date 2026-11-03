# GlucoShield Deployment & Production Operations Guide

**Module:** Deployment & Operations  
**Toolchain:** Docker (Multi-Stage), Python 3.12, Node.js v20+, Uvicorn, PostgreSQL / SQLite  
**Date:** November 3, 2026  

---

## 1. Local Development Quickstart

### Prerequisites
- Python 3.12+ (with pip)
- Node.js v20+ (with npm)
- Git

### Step 1: Environment Setup
```bash
git clone https://github.com/Sanjeeth-4AM/GlucoShield.git
cd GlucoShield

# Create virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Initialization & Migrations
```bash
# Copy local development template
cp .env.example .env

# Run database migrations
alembic upgrade head

# (Optional) Seed demo cohort patient profiles
python scripts/seed_demo_patient.py
```

### Step 3: Launch Services
In Terminal 1 (Backend API):
```bash
python -m uvicorn api.service:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation and interactive Swagger UI will be available at:  
`http://127.0.0.1:8000/docs`

In Terminal 2 (Frontend Client):
```bash
cd frontend
npm install
npm run dev
```
Client dashboard will be available at:  
`http://127.0.0.1:5173`

---

## 2. Production Docker Deployment

GlucoShield uses a multi-stage `Dockerfile` that compiles the React client assets into an optimized bundle and packages the FastAPI ASGI server with non-root security.

### Build and Run Docker Container
```bash
# Build production image
docker build -t glucoshield:latest .

# Run container with production environment
docker run -d \
  --name glucoshield-app \
  -p 8000:8000 \
  --env-file .env.production.template \
  glucoshield:latest
```

### Health Check Probes
- **Liveness Probe:** `GET http://localhost:8000/api/v1/health/live`
- **Readiness Probe:** `GET http://localhost:8000/api/v1/health/ready`
- **Comprehensive System Health:** `GET http://localhost:8000/api/v1/health`

---

## 3. Automated Testing Commands

### Backend Test Suite
```bash
# Run all core API unit and integration tests
python -m unittest api/tests/test_cohort_comparison.py
python -m unittest api/tests/test_database_models.py
python -m unittest api/tests/test_authentication_security.py
python -m unittest api/tests/test_patient_authorization.py
python -m unittest api/tests/test_device_endpoints.py
python -m unittest api/tests/test_persistence_endpoints.py
python -m unittest api/tests/test_longitudinal_analytics.py

# Run food vision multimodal pipeline tests
python -m unittest food_vision/tests/test_food_api_pipeline.py

# Run V2 factor and architecture tests
python -m unittest discover -s tests/v2

# Run certified Combination C serving certification test suite
python -m unittest tests/test_combination_c_serving.py
```

### Frontend Test Suite & Production Build
```bash
cd frontend

# Execute 114 unit & invariant verification tests
node --test src/api/api.test.js

# Compile production bundle
npm run build
```
