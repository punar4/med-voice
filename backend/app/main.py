"""FastAPI application. Routes are added task by task; see FREEBUFF_TASKS_v4.md."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from . import db, models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create missing tables before the first request, on SQLite or Postgres alike."""
    db.init_db()
    yield


app = FastAPI(title="Prescription Voice Assistant", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    """Liveness check. Must not touch the database."""
    return {"ok": True}


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int, session: Session = Depends(db.get_session)) -> dict:
    """Caregiver view: the profile plus all of its medicines, confirmed or not."""
    profile = session.get(models.Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    medicines = session.exec(
        select(models.Medicine).where(models.Medicine.profile_id == profile_id)
    ).all()
    return {"profile": profile, "medicines": medicines}
