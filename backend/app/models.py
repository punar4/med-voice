"""Database tables: Profile, Medicine and QuestionLog (section 5 of the task list).

Rule that later tasks must keep: the elder side only ever reads medicines where
`confirmed = true`.
"""

import secrets
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    """Timezone-aware timestamp, so ordering still works after a Postgres switch."""
    return datetime.now(timezone.utc)


def _share_token() -> str:
    return secrets.token_urlsafe(16)


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    elder_name: str
    language: str = "kn"
    share_token: str = Field(default_factory=_share_token, index=True, unique=True)
    created_at: datetime = Field(default_factory=_utcnow)


class Medicine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", index=True)

    name: str
    # aliases and times are JSON so the same column type works on SQLite and Postgres.
    aliases: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    label: str
    color_word: str
    photo_path: Optional[str] = None
    dose: str
    times: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    food: str = "any"  # "before" | "after" | "any"
    days_total: Optional[int] = None
    start_date: Optional[date] = None
    purpose: Optional[str] = None
    confirmed: bool = False


class QuestionLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", index=True)
    created_at: datetime = Field(default_factory=_utcnow)

    transcript: str
    intent: str
    medicine_id: Optional[int] = Field(default=None, foreign_key="medicine.id")
    outcome: str  # "answered" | "clarify" | "referral" | "emergency"
    answer_key: str
    answer_text: str
