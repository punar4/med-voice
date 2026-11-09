"""The file name we send decides how Prisma reads the clip (T1 real mode)."""

import unittest
from unittest import mock

import httpx

from app import config
from app.gnani import stt


class UploadFilenameTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = (config.MOCK_GNANI, config.GNANI_API_KEY, config.GNANI_BASE_URL)
        config.MOCK_GNANI = False
        config.GNANI_API_KEY = "test-key"
        config.GNANI_BASE_URL = "https://api.vachana.ai"

    def tearDown(self) -> None:
        config.MOCK_GNANI, config.GNANI_API_KEY, config.GNANI_BASE_URL = self._saved

    def _upload_part(self, **kwargs):
        response = httpx.Response(200, json={"success": True, "transcript": "ok"})
        with mock.patch.object(stt.httpx, "post", return_value=response) as post:
            stt.transcribe(b"clip-bytes", "kn", **kwargs)
        return post.call_args.kwargs["files"]["audio_file"]

    def test_real_file_name_sets_name_and_content_type(self) -> None:
        self.assertEqual(
            self._upload_part(filename="voice note.m4a"),
            ("voice note.m4a", b"clip-bytes", "audio/mp4"),
        )

    def test_without_file_name_stays_audio_wav(self) -> None:
        self.assertEqual(
            self._upload_part(),
            ("audio.wav", b"clip-bytes", "audio/wav"),
        )

    def test_unknown_extension_falls_back_to_octet_stream(self) -> None:
        self.assertEqual(
            self._upload_part(filename="recording.weird")[2],
            "application/octet-stream",
        )


if __name__ == "__main__":
    unittest.main()
