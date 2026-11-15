"""English answer text (shown on the English screen; only Kannada is spoken)."""

import json
from pathlib import Path

from app.core import answers

KN = json.loads((Path(answers.__file__).parent.parent / "templates" / "kn.json").read_text(encoding="utf-8"))
EN = json.loads((Path(answers.__file__).parent.parent / "templates" / "en.json").read_text(encoding="utf-8"))


def test_every_kannada_template_has_an_english_one():
    assert set(KN) == set(EN)


def test_english_answer_reads_naturally():
    times = answers.times_phrase(["night", "morning"], "en")
    text = answers.render("when", "en", label="ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ", times=times)
    assert text == "Take it in the morning and at night."  # the tablet is named in the tag above


def test_ask_returns_the_english_answer_too():
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from app import config
    from app.main import app

    with TestClient(app) as client:
        profile = client.post("/api/profiles", json={"elder_name": "English Test"}).json()
        tablet = client.post(
            f"/api/profiles/{profile['id']}/medicines",
            json={"name": "Amlodipine 5mg", "aliases": [], "label": "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ", "color_word": "ಬಿಳಿ",
                  "dose": "1 ಮಾತ್ರೆ", "times": ["morning"], "food": "after"},
        ).json()
        client.post(f"/api/medicines/{tablet['id']}/confirm")
        with patch.object(config, "MOCK_STT_TRANSCRIPT", "ಬಿಳಿ ಮಾತ್ರೆ ಊಟಕ್ಕೆ ಮುಂಚೆನಾ?"):
            body = client.post(
                f"/api/elder/{profile['share_token']}/ask", files={"audio": ("q.wav", b"x", "audio/wav")}
            ).json()
    assert body["outcome"] == "answered"
    assert body["answer_text_en"] == "Take it after food."


def test_ask_returns_every_tablet_with_its_photo():
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from app import config
    from app.main import app

    with TestClient(app) as client:
        profile = client.post("/api/profiles", json={"elder_name": "Photo Test"}).json()
        for label, colour, photo in (("ಬಿಳಿ ಮಾತ್ರೆ", "ಬಿಳಿ", "data:image/jpeg;base64,AAA"), ("ಹಳದಿ ಮಾತ್ರೆ", "ಹಳದಿ", None)):
            tablet = client.post(
                f"/api/profiles/{profile['id']}/medicines",
                json={"name": "X " + colour, "aliases": [], "label": label, "color_word": colour, "dose": "1 ಮಾತ್ರೆ",
                      "times": ["morning"], "food": "after", "photo_path": photo},
            ).json()
            client.post(f"/api/medicines/{tablet['id']}/confirm")
        url = f"/api/elder/{profile['share_token']}/ask"
        with patch.object(config, "MOCK_STT_TRANSCRIPT", "ಇವತ್ತು ಯಾವ ಮಾತ್ರೆ ತಗೋಬೇಕು?"):
            listed = client.post(url, files={"audio": ("q.wav", b"x", "audio/wav")}).json()
        with patch.object(config, "MOCK_STT_TRANSCRIPT", "ಬಿಳಿ ಮಾತ್ರೆ ಊಟಕ್ಕೆ ಮುಂಚೆನಾ?"):
            single = client.post(url, files={"audio": ("q.wav", b"x", "audio/wav")}).json()
    assert [m["label"] for m in listed["medicines"]] == ["ಬಿಳಿ ಮಾತ್ರೆ", "ಹಳದಿ ಮಾತ್ರೆ"]
    assert listed["medicines"][0]["photo_url"] == "data:image/jpeg;base64,AAA"
    assert [m["label"] for m in single["medicines"]] == ["ಬಿಳಿ ಮಾತ್ರೆ"]
