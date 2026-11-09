"""Prisma (Gnani) speech-to-text wrapper: transcribe(audio_bytes, lang) -> str.

Mock mode (MOCK_GNANI=true, the default) returns a fixed test transcript so the
rest of the app can be built without spending credits or needing an API key.
Real mode is deliberately unimplemented until the Prisma docs are pasted in.
"""

from .. import config
from . import GnaniNotConfigured


def transcribe(audio_bytes: bytes, lang: str = "kn") -> str:
    """Turn recorded audio into text the elder said, in the given language."""
    if config.MOCK_GNANI:
        return config.MOCK_STT_TRANSCRIPT

    # TODO(gnani-docs): endpoint, auth header, request body and response shape
    # are all unconfirmed. Ask the human for the Prisma part of docs.gnani.ai
    # before writing the real request; `audio_bytes` and `lang` are ignored today.
    raise GnaniNotConfigured(
        "Prisma (speech to text) real mode is not implemented yet. "
        "Paste the Gnani Prisma docs so the request can be written."
    )
