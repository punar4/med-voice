"""Prisma (Gnani) speech-to-text wrapper: transcribe(audio_bytes, lang) -> str.

Mock mode (MOCK_GNANI=true) returns a fixed test transcript so the rest of the
app can be built without spending credits. Real mode posts the clip to
`{GNANI_BASE_URL}/stt/v3` as multipart/form-data (docs pasted by the human).

Prisma accepts WAV, MP3, OGG, FLAC, AAC and M4A, up to 30 seconds. An empty
transcript means "no speech" and is returned as an empty string, not an error.
"""

import httpx

from .. import config
from . import (
    REQUEST_TIMEOUT_SECONDS,
    error_from_response,
    language_code,
    network_error,
    require_settings,
)

ENDPOINT = "/stt/v3"


def transcribe(
    audio_bytes: bytes,
    lang: str = "kn",
    keyterms: list[str] | None = None,
) -> str:
    """Turn recorded audio into text the elder said, in the given language.

    `keyterms` (medicine names to bias recognition) is accepted for a later
    tuning step but is not sent yet.
    """
    if config.MOCK_GNANI:
        return config.MOCK_STT_TRANSCRIPT

    base_url, api_key = require_settings("Prisma")
    try:
        response = httpx.post(
            f"{base_url}{ENDPOINT}",
            headers={"X-API-Key-ID": api_key},
            files={"audio_file": ("audio.wav", audio_bytes, "audio/wav")},
            data={
                "language_code": language_code(lang),
                "model": config.GNANI_STT_MODEL,
                "format": config.GNANI_STT_FORMAT,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise network_error("Prisma", exc) from exc

    if response.status_code != 200:
        raise error_from_response(response, "Prisma")

    try:
        payload = response.json()
    except ValueError:
        raise error_from_response(response, "Prisma") from None

    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise error_from_response(response, "Prisma")

    # "" means silence/unclear speech; the pipeline decides what to say then.
    return str(payload.get("transcript") or "")
