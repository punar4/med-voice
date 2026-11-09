"""Call the real Gnani services once, to check the wrappers and hear the voice.

Run from the repo root, with MOCK_GNANI=false and a real GNANI_API_KEY in .env:

    ../venv/Scripts/python.exe scripts/try_gnani.py path/to/clip.wav

Prints the Prisma transcript, asks Timbre to speak one fixed Kannada test
sentence (a plain greeting, not a medical answer), and saves out.wav.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config  # noqa: E402  (import after sys.path fix)
from app.gnani import GnaniNotConfigured  # noqa: E402
from app.gnani import stt, tts  # noqa: E402

# A greeting, so no medical answer text is invented here.
TEST_SENTENCE = "ನಮಸ್ಕಾರ, ಇದು ಧ್ವನಿ ಪರೀಕ್ಷೆ."
OUTPUT_PATH = ROOT / "out.wav"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/try_gnani.py <audio-file>")
        return 2

    if config.MOCK_GNANI:
        print("MOCK_GNANI is true, so nothing would reach Gnani.")
        print("Set MOCK_GNANI=false in .env (with GNANI_API_KEY and GNANI_BASE_URL) and run again.")
        return 1

    clip = Path(sys.argv[1])
    if not clip.is_file():
        print(f"audio file not found: {clip}")
        return 2

    try:
        transcript = stt.transcribe(clip.read_bytes(), "kn")
        print(f"Prisma transcript: {transcript!r}" if transcript else "Prisma: no speech detected")

        speech = tts.synthesize(TEST_SENTENCE, "kn")
        OUTPUT_PATH.write_bytes(speech)
        print(f"Timbre: {len(speech)} bytes of WAV saved to {OUTPUT_PATH}")
    except GnaniNotConfigured as exc:
        print(f"Gnani call failed: {exc}")
        return 1

    print(f"Play it with: start {OUTPUT_PATH}" if sys.platform == "win32" else f"Play it: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
