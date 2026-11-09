"""Database engine and session.

The only thing that differs between local and deployed is `DATABASE_URL`
(`sqlite:///./app.db` or `postgresql+psycopg://...`), so no code changes are
needed when switching.
"""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  (imported so SQLModel knows the tables)
from .config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    # SQLite only: FastAPI handles requests on several threads.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


def init_db() -> None:
    """Create any missing tables. Safe to call on every startup."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, closed afterwards."""
    with Session(engine) as session:
        yield session
