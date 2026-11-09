"""Configuration loaded from the repo-root .env file.

Never log or return the values of secret settings (GNANI_API_KEY in particular).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_BASE_URL = os.getenv("GNANI_BASE_URL", "")
MOCK_GNANI = _flag("MOCK_GNANI", "true")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Mock speech-to-text result, used while MOCK_GNANI=true. Not a secret; change it
# from the .env file (or here) to test a different question without a microphone.
MOCK_STT_TRANSCRIPT = os.getenv("MOCK_STT_TRANSCRIPT", "BP tablet yaavaga tegedukollabeku")

# Gnani request settings, used only when MOCK_GNANI=false. The defaults are the
# documented values; change them in .env rather than in code.
def _number(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, ""))
    except ValueError:
        return default


GNANI_STT_MODEL = os.getenv("GNANI_STT_MODEL", "prisma-v3.0")
GNANI_STT_FORMAT = os.getenv("GNANI_STT_FORMAT", "codemix")
# Send the elder's confirmed medicine words as Prisma `keyterms` (prisma-v3.0 only).
GNANI_STT_KEYTERMS = _flag("GNANI_STT_KEYTERMS", "true")
GNANI_TTS_MODEL = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")
GNANI_TTS_VOICE = os.getenv("GNANI_TTS_VOICE", "Saanvi")
GNANI_TTS_SPEED = _number("GNANI_TTS_SPEED", 0.9)
