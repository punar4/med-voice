"""'Which tablets do I take today?' answered only from confirmed prescription data."""

from datetime import date, timedelta

import pytest

from app.core import answers, pipeline
from app.models import Medicine

START = date.today() - timedelta(days=5)


def _meds(**extra):
    round_white = Medicine(
        id=1, profile_id=1, name="Amlodipine 5mg", aliases=["BP tablet"], label="ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ",
        color_word="ಬಿಳಿ", dose="1 ಮಾತ್ರೆ", times=["morning"], food="after", days_total=30,
        start_date=START, purpose="ಬಿಪಿ ಮಾತ್ರೆ", confirmed=True,
    )
    big_white = Medicine(
        id=2, profile_id=1, name="Metformin 500mg", aliases=["sugar tablet"], label="ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ",
        color_word="ಬಿಳಿ", dose="1 ಮಾತ್ರೆ", times=["morning", "night"], food="after", days_total=60,
        start_date=START, purpose=None, confirmed=True,
    )
    hidden = Medicine(
        id=3, profile_id=1, name="Paracetamol 650mg", aliases=[], label="ಉದ್ದ ಕಿತ್ತಳೆ ಮಾತ್ರೆ",
        color_word="ಕಿತ್ತಳೆ", dose="1 ಮಾತ್ರೆ", times=["night"], food="any", confirmed=False,
    )
    return [round_white, big_white, hidden]


def say(text, medicines, lang="kn"):
    decision = pipeline.decide(text, medicines, lang=lang)
    return decision, answers.render(decision.answer_key, lang, **decision.fields)


def test_todays_list_has_confirmed_tablets_only():
    decision, text = say("ಇವತ್ತು ಯಾವ ಮಾತ್ರೆ ತಗೋಬೇಕು?", _meds())
    assert decision.outcome == "answered"
    assert text == "ಇವತ್ತು ಬೆಳಿಗ್ಗೆ ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ ಮತ್ತೆ ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ, ರಾತ್ರಿ ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ ತಗೊಳ್ಳಿ."
    assert "ಕಿತ್ತಳೆ" not in text


def test_list_for_one_time_of_day():
    assert say("ರಾತ್ರಿ ಯಾವ ಮಾತ್ರೆ ತಗೋಬೇಕು?", _meds())[1] == "ರಾತ್ರಿ ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ ತಗೊಳ್ಳಿ."


def test_english_list():
    text = say("which tablets should i take today?", _meds(), lang="en")[1]
    assert text == "Today, take ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ and ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ in the morning; ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ at night."


def test_nothing_at_that_time_goes_to_the_doctor():
    assert say("ಮಧ್ಯಾಹ್ನ ಯಾವ ಮಾತ್ರೆ ತಗೋಬೇಕು?", _meds())[0].outcome == "referral"


@pytest.mark.parametrize("text", ["ನನಗೆ ತಲೆ ನೋವು, ಯಾವ ಮಾತ್ರೆ ತಗೊಳ್ಳಲಿ?", "ಜ್ವರ ಇದೆ, ಯಾವ ಮಾತ್ರೆ?", "which tablets for fever?"])
def test_symptom_is_never_answered_from_the_list(text):
    assert say(text, _meds())[0].outcome == "referral"


def test_finished_course_is_left_out():
    medicines = _meds()
    medicines[0].days_total = 3  # started 5 days ago: over
    text = say("ಇವತ್ತು ಯಾವ ಮಾತ್ರೆ ತಗೋಬೇಕು?", medicines)[1]
    assert "ಗುಂಡು" not in text and "ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ" in text


def test_emergency_still_wins():
    assert say("ಎಲ್ಲಾ ಮಾತ್ರೆ ತಗೊಂಡೆ", _meds())[0].outcome == "emergency"


def test_named_tablet_gets_its_times():
    decision, text = say("ದೊಡ್ಡ ಮಾತ್ರೆ ಯಾವ ಹೊತ್ತಿಗೆ ತಗೋಬೇಕು?", _meds())
    assert decision.outcome == "answered" and decision.medicine.label == "ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ"
