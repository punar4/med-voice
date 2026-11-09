"""Get uploaded audio into a format Prisma accepts (section 7, step 1).

Prisma takes WAV, MP3, OGG, FLAC, AAC and M4A, and picks its decoder from the
file name. Browsers usually record WebM (Chrome) or OGG (Firefox), so:
- formats Prisma accepts pass straight through, named by what the bytes really are;
- anything else (WebM, unknown) is converted with ffmpeg to 16 kHz mono WAV.

ffmpeg is a system program, not a Python package: it is installed in the Docker
image, and locally with `winget install ffmpeg` (Windows).
"""

import subprocess

# Uploads bigger than this are refused before any conversion work.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
FFMPEG_TIMEOUT_SECONDS = 30

ACCEPTED_BY_PRISMA = {"wav", "mp3", "ogg", "flac", "m4a"}


class AudioError(ValueError):
    """The upload cannot be turned into audio Prisma accepts."""


def sniff(data: bytes) -> str | None:
    """Name the container from its first bytes (the 'magic number')."""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"fLaC":
        return "flac"
    if data[4:8] == b"ftyp":
        return "m4a"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "mp3"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return None


def to_wav(data: bytes) -> bytes:
    """Convert any ffmpeg-readable audio to 16 kHz mono 16-bit WAV."""
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", "pipe:0",
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        "-f", "wav", "pipe:1",
    ]
    try:
        result = subprocess.run(
            command, input=data, capture_output=True, timeout=FFMPEG_TIMEOUT_SECONDS, check=False
        )
    except FileNotFoundError:
        raise AudioError("ffmpeg is not installed (Windows: winget install ffmpeg)") from None
    except subprocess.TimeoutExpired:
        raise AudioError("audio conversion took too long") from None
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode("utf-8", "replace").strip()[:200]
        raise AudioError(f"could not read the recording: {detail or 'unknown format'}")
    return result.stdout


def prepare_for_prisma(data: bytes) -> tuple[bytes, str]:
    """Return (audio_bytes, filename) that Prisma will decode correctly."""
    if not data:
        raise AudioError("empty recording")
    if len(data) > MAX_UPLOAD_BYTES:
        raise AudioError("recording is too large")
    kind = sniff(data)
    if kind in ACCEPTED_BY_PRISMA:
        return data, f"audio.{kind}"
    return to_wav(data), "audio.wav"
