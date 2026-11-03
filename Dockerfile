# GlucoShield Production Dockerfile
# ===================================
# Multi-stage build for a minimal, secure production image.
# Phase 16 Deployment Hardening.
#
# Usage:
#   docker build -t glucoshield:latest .
#   docker run -p 8000:8000 --env-file .env.production glucoshield:latest
#
# Health check: GET /api/v1/health/live

# ── Stage 1: Build Frontend ──────────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy package files first for layer caching
COPY frontend/package.json frontend/package-lock.json ./

RUN npm ci --silent

# Copy full frontend source
COPY frontend/ ./

# Production build
RUN npm run build

# ── Stage 2: Python Runtime ──────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1001 glucoshield \
    && useradd --uid 1001 --gid glucoshield --shell /bin/bash --create-home glucoshield

WORKDIR /app

# System dependencies (minimal set for PyTorch CPU/CUDA, SQLite, libgomp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libsqlite3-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY api/ ./api/
COPY neural/ ./neural/
COPY physiology/ ./physiology/
COPY decision_engine/ ./decision_engine/
COPY food_vision/ ./food_vision/
COPY db/ ./db/
COPY models/ ./models/
COPY data/metadata/ ./data/metadata/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Copy frozen Phase-13 gate and ODE configs
COPY scratch/phase13_disagreement_gate/frozen_gate_config.json ./scratch/phase13_disagreement_gate/
COPY scratch/phase13_patient_specific_ode/ode_adaptation_config.json ./scratch/phase13_patient_specific_ode/
COPY scratch/phase13_disagreement_gate/disagreement_gate.py ./scratch/phase13_disagreement_gate/
COPY scratch/phase13_patient_specific_ode/patient_ode_adapter.py ./scratch/phase13_patient_specific_ode/

# Copy built frontend dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# Set correct ownership
RUN chown -R glucoshield:glucoshield /app

USER glucoshield

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=PRODUCTION

# Expose port
EXPOSE 8000

# Health check — polls liveness probe every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

# Entrypoint: uvicorn with production settings
CMD ["python", "-m", "uvicorn", "api.service:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--timeout-keep-alive", "30", \
     "--access-log"]
