"""FastAPI application. Routes are added task by task; see FREEBUFF_TASKS_v4.md."""

from contextlib import asynccontextmanager
from datetime import date
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from . import db, models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create missing tables before the first request, on SQLite or Postgres alike."""
    db.init_db()
    yield


app = FastAPI(title="Prescription Voice Assistant", lifespan=lifespan)


class ProfileCreate(BaseModel):
    """What the caregiver types to start: the elder's name (display only)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    elder_name: str = Field(min_length=1, max_length=120)
    language: str = "kn"


class MedicineInput(BaseModel):
    """Every medicine field from section 5 that the caregiver fills in.

    `confirmed` is deliberately absent: only the confirm route may set it, and
    editing always clears it again.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    aliases: list[str] = Field(default_factory=list)
    label: str = Field(min_length=1, max_length=120)
    color_word: str = Field(min_length=1, max_length=40)
    photo_path: str | None = None
    dose: str = Field(min_length=1, max_length=80)
    times: list[Literal["morning", "afternoon", "night"]] = Field(default_factory=list)
    food: Literal["before", "after", "any"] = "any"
    days_total: int | None = Field(default=None, ge=1)
    start_date: date | None = None
    purpose: str | None = None


def _get_profile(session: Session, profile_id: int) -> models.Profile:
    profile = session.get(models.Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile


def _get_medicine(session: Session, medicine_id: int) -> models.Medicine:
    medicine = session.get(models.Medicine, medicine_id)
    if medicine is None:
        raise HTTPException(status_code=404, detail="medicine not found")
    return medicine


def _save(session: Session, row):
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@app.get("/api/health")
def health() -> dict:
    """Liveness check. Must not touch the database."""
    return {"ok": True}


@app.post("/api/profiles", status_code=201)
def create_profile(payload: ProfileCreate, session: Session = Depends(db.get_session)) -> dict:
    """Start a profile for one elder and hand back the token that makes the elder link."""
    profile = _save(session, models.Profile(**payload.model_dump()))
    return {"id": profile.id, "share_token": profile.share_token}


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int, session: Session = Depends(db.get_session)) -> dict:
    """Caregiver view: the profile plus all of its medicines, confirmed or not."""
    profile = _get_profile(session, profile_id)
    medicines = session.exec(
        select(models.Medicine).where(models.Medicine.profile_id == profile_id)
    ).all()
    return {"profile": profile, "medicines": medicines}


@app.post("/api/profiles/{profile_id}/medicines", status_code=201)
def add_medicine(
    profile_id: int,
    payload: MedicineInput,
    session: Session = Depends(db.get_session),
) -> models.Medicine:
    """Add a medicine for this profile. It starts unconfirmed, so the elder cannot see it yet."""
    _get_profile(session, profile_id)
    medicine = models.Medicine(profile_id=profile_id, confirmed=False, **payload.model_dump())
    return _save(session, medicine)


@app.put("/api/medicines/{medicine_id}")
def update_medicine(
    medicine_id: int,
    payload: MedicineInput,
    session: Session = Depends(db.get_session),
) -> models.Medicine:
    """Replace a medicine's details and un-confirm it: an edited field must be re-checked."""
    medicine = _get_medicine(session, medicine_id)
    for field, value in payload.model_dump().items():
        setattr(medicine, field, value)
    medicine.confirmed = False
    return _save(session, medicine)


@app.post("/api/medicines/{medicine_id}/confirm")
def confirm_medicine(medicine_id: int, session: Session = Depends(db.get_session)) -> models.Medicine:
    """Caregiver says the details are correct; only now can the elder hear about it."""
    medicine = _get_medicine(session, medicine_id)
    medicine.confirmed = True
    return _save(session, medicine)


@app.delete("/api/medicines/{medicine_id}", status_code=204)
def delete_medicine(medicine_id: int, session: Session = Depends(db.get_session)) -> Response:
    """Remove a medicine, e.g. one added by mistake."""
    medicine = _get_medicine(session, medicine_id)
    session.delete(medicine)
    session.commit()
    return Response(status_code=204)
