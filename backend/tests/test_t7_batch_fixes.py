"""T7: general bugs found by the first real-voice batch run (25/38 untouched).

Each test is a general rule, not a test sentence: elders shorten tablet names,
mix in English describing words, and ask to change doses.
"""

from datetime import date, timedelta

from app.core import intent, pipeline
from app.core.matching import match
from app.models import Medicine

START = date.today() - timedelta(days=5)


def _meds():
    round_white = Medicine(
        id=1, profile_id=1, name="Amlodipine 5mg", aliases=["BP tablet", "bili"],
        label="ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ", color_word="ಬಿಳಿ", dose="1 ಮಾತ್ರೆ", times=["morning"],
        food="after", days_total=30, start_date=START, purpose="ಬಿಪಿ ಮಾತ್ರೆ", confirmed=True,
    )
    big_white = Medicine(
        id=2, profile_id=1, name="Metformin 500mg", aliases=["sugar tablet", "bili"],
        label="ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ", color_word="ಬಿಳಿ", dose="1 ಮಾತ್ರೆ", times=["morning", "night"],
        food="after", days_total=60, start_date=START, purpose=None, confirmed=True,
    )
    return round_white, big_white


def test_label_without_colour_finds_the_tablet():
    round_white, big_white = _meds()
    assert match("ಗುಂಡು ಮಾತ್ರೆ ಎಷ್ಟು ತಗೋಬೇಕು?", [round_white, big_white]).medicine is round_white
    assert match("ದೊಡ್ಡ ಮಾತ್ರೆ ದಿನಕ್ಕೆ ಎಷ್ಟು?", [round_white, big_white]).medicine is big_white


def test_colour_alone_is_still_ambiguous():
    assert match("ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ?", list(_meds())).ambiguous


def test_both_distinct_words_is_ambiguous_not_a_guess():
    result = match("ಗುಂಡು ಮಾತ್ರೆನಾ ದೊಡ್ಡ ಮಾತ್ರೆನಾ?", list(_meds()))
    assert result.medicine is None


def test_english_descriptors():
    round_white, big_white = _meds()
    assert match("Big white tablet, how many?", [round_white, big_white]).medicine is big_white
    assert match("ರೌಂಡ್ ಮಾತ್ರೆ ಯಾವಾಗ?", [round_white, big_white]).medicine is round_white


def test_english_colour_not_confirmed_is_unlisted():
    assert match("orange tablet when?", list(_meds())).unlisted


def test_dose_change_always_goes_to_the_doctor():
    assert intent.detect("Doctor ಕೇಳದೆ dose ಜಾಸ್ತಿ ಮಾಡಬಹುದಾ?") == intent.CHANGE
    for text in ("ಗುಂಡು ಮಾತ್ರೆ ನಿಲ್ಲಿಸಬಹುದಾ?", "can I skip the big white tablet?", "ದೊಡ್ಡ ಮಾತ್ರೆ ಕಮ್ಮಿ ಮಾಡ್ಲಾ?"):
        assert pipeline.decide(text, list(_meds())).outcome == pipeline.REFERRAL


def test_unknown_question_about_short_name_asks_back():
    assert pipeline.decide("ಗುಂಡು ಮಾತ್ರೆ ಬಗ್ಗೆ ಹೇಳಿ.", list(_meds())).outcome == pipeline.CLARIFY_QUESTION


def test_missing_purpose_refers():
    assert pipeline.decide("ಈ ದೊಡ್ಡ ಮಾತ್ರೆ ಯಾತಕ್ಕೆ?", list(_meds())).outcome == pipeline.REFERRAL
