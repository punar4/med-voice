"""FastAPI application. Routes are added task by task; see FREEBUFF_TASKS_v4.md."""

import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlmodel import Session, select

from . import db, models
from .audio import MAX_UPLOAD_BYTES
from .core import pipeline
from .core.matching import with_colour_alias

logger = logging.getLogger(__name__)

# Where `npm run build` leaves the frontend. The Docker image copies the same
# folder in, so the deployed app serves API and UI from one origin (mic access
# needs HTTPS on a single origin, not a separate static host).
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


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


@app.get("/api/health/db")
def health_db(session: Session = Depends(db.get_session)) -> dict:
    """Readiness check: one round trip to the database (the keep-alive ping).

    Returns 503 instead of 500 so a sleeping or unreachable Postgres reads as
    "not ready yet" rather than a crash.
    """
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any driver/connection error means not ready
        logger.warning("database health check failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="database unavailable") from None
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
    data = payload.model_dump()
    data["aliases"] = with_colour_alias(data["aliases"], data["color_word"])
    medicine = models.Medicine(profile_id=profile_id, confirmed=False, **data)
    return _save(session, medicine)


@app.put("/api/medicines/{medicine_id}")
def update_medicine(
    medicine_id: int,
    payload: MedicineInput,
    session: Session = Depends(db.get_session),
) -> models.Medicine:
    """Replace a medicine's details and un-confirm it: an edited field must be re-checked."""
    medicine = _get_medicine(session, medicine_id)
    data = payload.model_dump()
    data["aliases"] = with_colour_alias(data["aliases"], data["color_word"])
    for field, value in data.items():
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


@app.get("/api/profiles/{profile_id}/log")
def question_log(profile_id: int, session: Session = Depends(db.get_session)) -> list[models.QuestionLog]:
    """Caregiver view: what the elder asked and what they were told, newest first."""
    _get_profile(session, profile_id)
    return list(
        session.exec(
            select(models.QuestionLog)
            .where(models.QuestionLog.profile_id == profile_id)
            .order_by(models.QuestionLog.created_at.desc(), models.QuestionLog.id.desc())
            .limit(200)
        ).all()
    )


def _get_elder_profile(session: Session, token: str) -> models.Profile:
    profile = session.exec(select(models.Profile).where(models.Profile.share_token == token)).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="link not found")
    return profile


@app.get("/api/elder/{token}")
def elder_view(token: str, session: Session = Depends(db.get_session)) -> dict:
    """Elder page data: language plus confirmed medicines' labels and photos only."""
    profile = _get_elder_profile(session, token)
    medicines = session.exec(
        select(models.Medicine).where(
            models.Medicine.profile_id == profile.id,
            models.Medicine.confirmed == True,  # noqa: E712
        )
    ).all()
    return {
        "language": profile.language,
        "medicines": [
            {"label": medicine.label, "photo_url": medicine.photo_path} for medicine in medicines
        ],
    }


@app.post("/api/elder/{token}/ask")
async def elder_ask(
    token: str,
    audio: UploadFile = File(...),
    session: Session = Depends(db.get_session),
) -> dict:
    """One spoken question in, one spoken answer out (see core/pipeline.py)."""
    profile = _get_elder_profile(session, token)
    data = await audio.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="recording is too large")
    result = pipeline.run(session, profile, data)
    return {
        "transcript": result.transcript,
        "outcome": result.outcome,
        "answer_text": result.answer_text,
        "audio_base64": result.audio_base64,
        "medicine": result.medicine,
        "audio_error": result.audio_error,
    }


# --- Frontend (built by `npm run build`, served by this same app) -------------
# Everything above is the API. The two handlers below are declared last so real
# routes always win, and they never answer for a missing /api path.

if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str) -> FileResponse:
    """Serve a built file, or `index.html` so client routes like /elder/<token> work.

    Without the fallback, refreshing the elder's link returns 404 because the
    server has no file at that path: the page is chosen in the browser.
    """
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    root = FRONTEND_DIST.resolve()
    candidate = (root / full_path).resolve()
    if full_path and candidate.is_relative_to(root) and candidate.is_file():
        return FileResponse(candidate)

    index = root / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(
        status_code=404,
        detail="frontend build not found: run `npm run build` in frontend/",
    )
