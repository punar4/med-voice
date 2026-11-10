# One image, two stages: Node builds the React app, then a slim Python image
# installs ffmpeg + the backend and serves both from a single origin.
# Render builds this file directly; no registry or CI needed.

# --- Stage 1: build the frontend -------------------------------------------
FROM node:22-slim AS frontend

WORKDIR /build

# Copy the lockfile first so `npm ci` is cached until dependencies change.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: API + UI ------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg is a system program used by app/audio.py, so the image must ship it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend /build/dist ./frontend/dist

# config.py finds the repo root two levels above backend/app, so .env lookup
# still resolves to /app/.env (absent in the image: settings come from Render).
WORKDIR /app/backend

EXPOSE 8000

# Shell form so ${PORT} is expanded; Render sets PORT, locally it defaults 8000.
CMD uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
