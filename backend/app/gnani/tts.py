"""Timbre (Gnani) text-to-speech wrapper: synthesize(text, lang) -> bytes.

Mock mode (MOCK_GNANI=true) returns a short silent WAV so the frontend can
autoplay real audio bytes before Timbre is wired up. Real mode posts JSON to
`{GNANI_BASE_URL}/api/v1/tts/inference` and gets raw WAV bytes back.
"""

import io
import wave

import httpx

from .. import config
from . import (
    REQUEST_TIMEOUT_SECONDS,
    error_from_response,
    language_code,
    network_error,
    require_settings,
)

ENDPOINT = "/api/v1/tts/inference"

# The 44-byte WAV header every browser-playable clip starts with.
WAV_MAGIC = b"RIFF"

# Mock clip: 0.5 seconds of 16-bit mono 16 kHz silence, built with the stdlib
# `wave` module so mock mode needs no extra dependency.
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

# Output format asked of Timbre; the frontend plays this directly.
AUDIO_CONFIG = {
    "sample_rate": 24000,
    "num_channels": 1,
    "sample_width": 2,
    "encoding": "linear_pcm",
    "container": "wav",
}


def synthesize(text: str, lang: str = "kn") -> bytes:
    """Speak `text` aloud in the given language; returns WAV file bytes."""
    if config.MOCK_GNANI:
        return MOCK_SILENCE

    base_url, api_key = require_settings("Timbre")
    body = {
        "text": text,
        "model": config.GNANI_TTS_MODEL,
        "voice": config.GNANI_TTS_VOICE,
        "language": language_code(lang),
        "speed": config.GNANI_TTS_SPEED,
        "audio_config": AUDIO_CONFIG,
    }
    try:
        response = httpx.post(
            f"{base_url}{ENDPOINT}",
            headers={"X-API-Key-ID": api_key},
            json=body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise network_error("Timbre", exc) from exc

    if response.status_code != 200:
        raise error_from_response(response, "Timbre")

    audio = response.content
    if not audio.startswith(WAV_MAGIC):
        # A 200 that is not audio means an error body slipped through; report it
        # rather than handing broken bytes to the browser.
        raise error_from_response(response, "Timbre")
    return audio
