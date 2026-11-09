"""T4: the elder routes, the question log, keyterms on the wire and audio prep."""

import json
import shutil
import subprocess
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app import audio, config
from app.gnani import stt
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _setup(client):
    profile = client.post("/api/profiles", json={"elder_name": "Test Elder"}).json()
    body = {
        "name": "Amlodipine 5mg", "aliases": ["BP tablet"], "label": "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ",
        "color_word": "ಬಿಳಿ", "dose": "1 ಮಾತ್ರೆ", "times": ["morning", "night"], "food": "after",
    }
    white = client.post(f"/api/profiles/{profile['id']}/medicines", json=body).json()
    hidden = client.post(
        f"/api/profiles/{profile['id']}/medicines",
        json={**body, "label": "ಉದ್ದ ಕಿತ್ತಳೆ ಮಾತ್ರೆ", "color_word": "ಕಿತ್ತಳೆ"},
    ).json()
    client.post(f"/api/medicines/{white['id']}/confirm")
    return profile, white, hidden


def test_colour_alias_added_on_save(client):
    _, white, _ = _setup(client)
    assert white["aliases"] == ["BP tablet", "bili"]


def test_elder_view_shows_confirmed_medicines_only(client):
    profile, _, _ = _setup(client)
    view = client.get(f"/api/elder/{profile['share_token']}").json()
    assert [m["label"] for m in view["medicines"]] == ["ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ"]
    assert client.get("/api/elder/not-a-token").status_code == 404


def test_ask_answers_speaks_and_logs(client):
    profile, white, _ = _setup(client)
    with patch.object(config, "MOCK_STT_TRANSCRIPT", "ಈ ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?"):
        response = client.post(
            f"/api/elder/{profile['share_token']}/ask",
            files={"audio": ("q.webm", b"fake-audio", "audio/webm")},
        )
    body = response.json()
    assert response.status_code == 200
    assert body["outcome"] == "answered"
    assert body["answer_text"] == "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ. ಇದನ್ನ ಬೆಳಿಗ್ಗೆ ಮತ್ತೆ ರಾತ್ರಿ ತಗೊಳ್ಳಿ."
    assert body["audio_base64"]
    assert body["medicine"]["label"] == "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ"

    entries = client.get(f"/api/profiles/{profile['id']}/log").json()
    assert entries[0]["outcome"] == "answered"
    assert entries[0]["medicine_id"] == white["id"]


def test_ask_emergency_is_logged(client):
    profile, _, _ = _setup(client)
    with patch.object(config, "MOCK_STT_TRANSCRIPT", "ಎದೆ ನೋವು ಆಗ್ತಿದೆ"):
        body = client.post(
            f"/api/elder/{profile['share_token']}/ask", files={"audio": ("q.webm", b"x", "audio/webm")}
        ).json()
    assert body["outcome"] == "emergency"
    assert "ಸೊನ್ನೆ ಎಂಟು" in body["answer_text"]
    assert client.get(f"/api/profiles/{profile['id']}/log").json()[0]["outcome"] == "emergency"


def test_follow_up_through_the_route(client):
    profile, _, _ = _setup(client)
    url = f"/api/elder/{profile['share_token']}/ask"
    with patch.object(config, "MOCK_STT_TRANSCRIPT", "ಇದನ್ನ ಹಾಲಿನ ಜೊತೆ ತಗೋಬಹುದಾ?"):
        first = client.post(url, files={"audio": ("q.webm", b"x", "audio/webm")}).json()
        second = client.post(url, files={"audio": ("q.webm", b"x", "audio/webm")}).json()
    assert first["outcome"] == "clarify_question"
    assert second["outcome"] == "referral"


def test_no_speech_asks_again(client):
    profile, _, _ = _setup(client)
    with patch.object(config, "MOCK_STT_TRANSCRIPT", ""):
        body = client.post(
            f"/api/elder/{profile['share_token']}/ask", files={"audio": ("q.webm", b"x", "audio/webm")}
        ).json()
    assert body["outcome"] == "error"


# --- Prisma keyterms on the wire --------------------------------------------------

class _Ok:
    status_code = 200

    def json(self):
        return {"success": True, "transcript": "ok"}


class _InvalidContext:
    status_code = 400
    text = ""
    reason_phrase = "Bad Request"

    def json(self):
        return {"success": False, "error": {"type": "INVALID_CONTEXT", "message": "too many"}}


@pytest.fixture()
def real_mode():
    saved = (config.MOCK_GNANI, config.GNANI_BASE_URL, config.GNANI_API_KEY, config.GNANI_STT_MODEL)
    config.MOCK_GNANI, config.GNANI_BASE_URL, config.GNANI_API_KEY = False, "https://example.test", "k"
    config.GNANI_STT_MODEL = "prisma-v3.0"
    yield
    config.MOCK_GNANI, config.GNANI_BASE_URL, config.GNANI_API_KEY, config.GNANI_STT_MODEL = saved


def test_keyterms_sent_as_json_array(real_mode):
    with patch.object(httpx, "post", return_value=_Ok()) as post:
        stt.transcribe(b"x", "kn", keyterms=["ಬಿಳಿ", "ಬಿಳಿ", "ಮಾತ್ರೆ"], filename="a.wav")
    assert json.loads(post.call_args.kwargs["data"]["keyterms"]) == ["ಬಿಳಿ", "ಮಾತ್ರೆ"]


def test_keyterms_not_sent_on_v25(real_mode):
    config.GNANI_STT_MODEL = "prisma-v2.5"
    with patch.object(httpx, "post", return_value=_Ok()) as post:
        stt.transcribe(b"x", "kn", keyterms=["ಬಿಳಿ"], filename="a.wav")
    assert "keyterms" not in post.call_args.kwargs["data"]


def test_invalid_context_retries_without_keyterms(real_mode):
    with patch.object(httpx, "post", side_effect=[_InvalidContext(), _Ok()]) as post:
        assert stt.transcribe(b"x", "kn", keyterms=["ಬಿಳಿ"], filename="a.wav") == "ok"
    assert "keyterms" in post.call_args_list[0].kwargs["data"]
    assert "keyterms" not in post.call_args_list[1].kwargs["data"]


# --- Audio preparation --------------------------------------------------------------

def test_accepted_formats_pass_through():
    wav = b"RIFF\x00\x00\x00\x00WAVEfmt "
    assert audio.prepare_for_prisma(wav) == (wav, "audio.wav")
    assert audio.prepare_for_prisma(b"OggS....")[1] == "audio.ogg"
    assert audio.prepare_for_prisma(b"\x00\x00\x00\x20ftypM4A ")[1] == "audio.m4a"


def test_empty_recording_is_rejected():
    with pytest.raises(audio.AudioError):
        audio.prepare_for_prisma(b"")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_browser_webm_is_converted_to_wav():
    webm = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         "sine=frequency=440:duration=1", "-c:a", "libopus", "-f", "webm", "pipe:1"],
        capture_output=True, check=True,
    ).stdout
    assert audio.sniff(webm) == "webm"
    data, name = audio.prepare_for_prisma(webm)
    assert name == "audio.wav" and audio.sniff(data) == "wav"
