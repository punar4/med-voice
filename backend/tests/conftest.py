"""Test settings, applied before the app is imported.

Tests always run in mock mode on a throwaway SQLite file, whatever `.env` says,
so they never spend Gnani credits or touch your real app.db.
(python-dotenv does not override variables that are already set.)
"""

import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.mkdtemp(prefix="medvoice-tests-")) / "test.db"

os.environ["MOCK_GNANI"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
