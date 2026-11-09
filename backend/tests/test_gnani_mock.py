"""T1 smoke test: both Gnani wrappers return usable mock results.

Run from `backend/` with:  ../venv/Scripts/python.exe -m unittest discover -s tests -t .
Uses the stdlib `unittest`, so no extra dependency is needed.
"""

import io
import unittest
import wave

from app import config
from app.gnani import stt, tts


class SttMockTest(unittest.TestCase):
    def test_returns_the_configured_transcript(self):
        transcript = stt.transcribe(b"pretend-audio", "kn")
        self.assertEqual(transcript, config.MOCK_STT_TRANSCRIPT)

    def test_transcript_is_usable_text(self):
        transcript = stt.transcribe(b"pretend-audio", "kn")
        self.assertIsInstance(transcript, str)
        self.assertTrue(transcript.strip())


class TtsMockTest(unittest.TestCase):
    def setUp(self):
        self.audio = tts.synthesize("mock answer", "kn")

    def test_returns_bytes(self):
        self.assertIsInstance(self.audio, bytes)

    def test_is_a_valid_silent_wav(self):
        self.assertEqual(self.audio[:4], b"RIFF")
        with wave.open(io.BytesIO(self.audio)) as wav:
            self.assertEqual(wav.getnchannels(), tts.MOCK_CHANNELS)
            self.assertEqual(wav.getframerate(), tts.MOCK_SAMPLE_RATE)
            frames = wav.readframes(wav.getnframes())
        self.assertGreater(len(frames), 0)
        self.assertEqual(set(frames), {0})  # every sample is zero => silence


if __name__ == "__main__":
    unittest.main()
