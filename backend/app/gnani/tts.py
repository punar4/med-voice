"""Timbre (Gnani) text-to-speech wrapper: synthesize(text, lang) -> bytes.

Mock mode (MOCK_GNANI=true, the default) returns a short silent WAV so the
frontend can autoplay real audio bytes before Timbre is wired up. Real mode is
deliberately unimplemented until the Timbre docs are pasted in.
"""

import io
import wave

from .. import config
from . import GnaniNotConfigured

# The mock clip: 0.5 seconds of 16-bit mono 16 kHz silence, built by the stdlib
# `wave` module so no extra dependency is needed.
MOCK_SAMPLE_RATE = 16_000
MOCK_CHANNELS = 1
MOCK_SAMPLE_WIDTH = 2  # bytes per sample (16-bit)
MOCK_SECONDS = 0.5


def _silent_wav() -> bytes:
    """Build a valid WAV file of silence, playable by any browser."""
    frame_count = int(MOCK_SAMPLE_RATE * MOCK_SECONDS)
    sample = b"\x00" * (frame_count * MOCK_SAMPLE_WIDTH * MOCK_CHANNELS)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(MOCK_CHANNELS)
        wav.setsampwidth(MOCK_SAMPLE_WIDTH)
        wav.setframerate(MOCK_SAMPLE_RATE)
        wav.writeframes(sample)
    return buffer.getvalue()


MOCK_SILENCE = _silent_wav()


def synthesize(text: str, lang: str = "kn") -> bytes:
    """Speak `text` aloud in the given language; returns audio file bytes."""
    if config.MOCK_GNANI:
        return MOCK_SILENCE

    # TODO(gnani-docs): endpoint, auth header, request body (voice, speed,
    # output format) and response shape are all unconfirmed. Ask the human for
    # the Timbre part of docs.gnani.ai before writing the real request.
    raise GnaniNotConfigured(
        "Timbre (text to speech) real mode is not implemented yet. "
        "Paste the Gnani Timbre docs so the request can be written."
    )
