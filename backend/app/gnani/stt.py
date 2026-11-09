"""Prisma (Gnani) speech-to-text wrapper: transcribe(audio_bytes, lang, filename) -> str.

Mock mode (MOCK_GNANI=true) returns a fixed test transcript so the rest of the
app can be built without spending credits. Real mode posts the clip to
`{GNANI_BASE_URL}/stt/v3` as multipart/form-data (docs pasted by the human).

Prisma accepts WAV, MP3, OGG, FLAC, AAC and M4A, up to 30 seconds. An empty
transcript means "no speech" and is returned as an empty string, not an error.
"""

import json
import logging
import mimetypes

import httpx

from .. import config
from . import (
    GnaniAPIError,
    REQUEST_TIMEOUT_SECONDS,
    error_from_response,
    language_code,
    network_error,
    require_settings,
)

logger = logging.getLogger(__name__)

ENDPOINT = "/stt/v3"
DEFAULT_FILENAME = "audio.wav"
DEFAULT_CONTENT_TYPE = "audio/wav"

# Docs: keyterms work only on prisma-v3.0, up to 200 entries; more returns
# 400 INVALID_CONTEXT. We cap well below that.
KEYTERMS_MODEL = "prisma-v3.0"
MAX_KEYTERMS = 100
INVALID_CONTEXT = "INVALID_CONTEXT"


def _upload_part(audio_bytes: bytes, filename: str | None) -> tuple[str, bytes, str]:
    """Build the multipart part, naming and typing the file as it really is.

    Prisma trusts the file name/type over the bytes: an M4A clip labelled
    .wav fails with `AUDIO_CONVERSION_ERROR` ("invalid start code in RIFF
    header"), so callers should pass the real file name.
    """
    if filename is None:
        return DEFAULT_FILENAME, audio_bytes, DEFAULT_CONTENT_TYPE
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return filename, audio_bytes, content_type


def transcribe(
    audio_bytes: bytes,
    lang: str = "kn",
    keyterms: list[str] | None = None,
    filename: str | None = None,
) -> str:
    """Turn recorded audio into text the elder said, in the given language.

    `keyterms` (the elder's medicine words) bias recognition towards those
    words; they are sent only on prisma-v3.0 with GNANI_STT_KEYTERMS on, and if
    Prisma rejects them (400 INVALID_CONTEXT) the call is retried once without.
    `filename` names the uploaded file so Prisma detects the real format.
    """
    if config.MOCK_GNANI:
        return config.MOCK_STT_TRANSCRIPT

    terms = _keyterms(keyterms)
    try:
        return _call(audio_bytes, lang, filename, terms)
    except GnaniAPIError as exc:
        if terms and exc.status_code == 400 and exc.error_type == INVALID_CONTEXT:
            logger.warning("Prisma rejected keyterms (INVALID_CONTEXT); retrying without them")
            return _call(audio_bytes, lang, filename, None)
        raise


def _keyterms(keyterms: list[str] | None) -> list[str] | None:
    if not keyterms or not config.GNANI_STT_KEYTERMS or config.GNANI_STT_MODEL != KEYTERMS_MODEL:
        return None
    unique = list(dict.fromkeys(term.strip() for term in keyterms if term and term.strip()))
    return unique[:MAX_KEYTERMS] or None


def _call(audio_bytes: bytes, lang: str, filename: str | None, keyterms: list[str] | None) -> str:
    base_url, api_key = require_settings("Prisma")
    data = {
        "language_code": language_code(lang),
        "model": config.GNANI_STT_MODEL,
        "format": config.GNANI_STT_FORMAT,
    }
    if keyterms:
        data["keyterms"] = json.dumps(keyterms, ensure_ascii=False)
    try:
        response = httpx.post(
            f"{base_url}{ENDPOINT}",
            headers={"X-API-Key-ID": api_key},
            files={"audio_file": _upload_part(audio_bytes, filename)},
            data=data,
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
