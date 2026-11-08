"""FastAPI application. Routes are added task by task; see FREEBUFF_TASKS_v3.md."""

from fastapi import FastAPI

app = FastAPI(title="Prescription Voice Assistant")


@app.get("/api/health")
def health() -> dict:
    """Liveness check. Must not touch the database."""
    return {"ok": True}
