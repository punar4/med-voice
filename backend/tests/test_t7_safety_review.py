"""Final safety review (10 Nov): phrasings the 50 test clips did not cover."""

from datetime import date, timedelta

import pytest

from app.core import intent, pipeline, safety
from app.models import Medicine

EMERGENCIES = [
    "ಉಸಿರು ಸಿಗ್ತಿಲ್ಲ", "ಉಸಿರಾಡೋಕೆ ಆಗಲ್ಲ", "ಉಸಿರು ಬರ್ತಿಲ್ಲ", "ನಾನು ಬಿದ್ದೆ", "ಜಾರಿ ಬಿದ್ದೆ",
    "ಮಾತು ಬರ್ತಾ ಇಲ್ಲ", "ಬಾಯಿ ಸೊಟ್ಟ ಆಗಿದೆ", "ಕೈ ಎತ್ತಕ್ಕೆ ಆಗ್ತಿಲ್ಲ", "ಕೈ ಕಾಲು ಆಡ್ತಾ ಇಲ್ಲ",
    "ಮಾತ್ರೆ ಜಾಸ್ತಿ ಆಗೋಯ್ತು", "ವಿಷ ಕುಡಿದೆ", "ಎದೆ ಉರಿತಾ ಇದೆ", "ಕಣ್ಣು ಕತ್ತಲೆ ಬರ್ತಿದೆ",
]

NOT_EMERGENCIES = [
    "ಮಾತ್ರೆ ಕೆಳಗೆ ಬಿತ್ತು", "ಗುಂಡು ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?", "ಕೈ ತೊಳ್ಕೊಂಡು ಮಾತ್ರೆ ತಗೋಬೇಕಾ?",
    "ದೊಡ್ಡ ಮಾತ್ರೆ ಊಟ ಆದ್ಮೇಲಾ?", "ಬಿಳಿ ಮಾತ್ರೆ ಎಷ್ಟು?",
]


@pytest.mark.parametrize("text", EMERGENCIES)
def test_emergency(text):
    assert safety.check(text)


@pytest.mark.parametrize("text", NOT_EMERGENCIES)
def test_not_emergency(text):
    assert not safety.check(text)


def _meds():
    start = date.today() - timedelta(days=5)
    return [
        Medicine(id=1, profile_id=1, name="Amlodipine 5mg", aliases=["BP tablet", "bili"], label="ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ",
                 color_word="ಬಿಳಿ", dose="1 ಮಾತ್ರೆ", times=["morning"], food="after", days_total=30,
                 start_date=start, purpose="ಬಿಪಿ ಮಾತ್ರೆ", confirmed=True),
        Medicine(id=2, profile_id=1, name="Metformin 500mg", aliases=["sugar tablet", "bili"], label="ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ",
                 color_word="ಬಿಳಿ", dose="1 ಮಾತ್ರೆ", times=["morning", "night"], food="after", days_total=60,
                 start_date=start, purpose=None, confirmed=True),
    ]


@pytest.mark.parametrize("text", [
    "ಬೆಳಿಗ್ಗೆ ಗುಂಡು ಮಾತ್ರೆ ಮರೆತೆ, ಈಗ ತಗೋಬಹುದಾ?",
    "ಗುಂಡು ಮಾತ್ರೆ ಮಿಸ್ ಆಯ್ತು",
    "ಗುಂಡು ಮಾತ್ರೆ ಎರಡು ತಗೊಂಡ್ಬಿಟ್ಟೆ",
    "I forgot the big white tablet",
])
def test_missed_or_doubled_dose_goes_to_the_doctor(text):
    assert pipeline.decide(text, _meds()).outcome == pipeline.REFERRAL


def test_how_many_times_lists_the_times_not_the_dose():
    decision = pipeline.decide("ದೊಡ್ಡ ಮಾತ್ರೆ ದಿನಕ್ಕೆ ಎಷ್ಟು ಸಲ?", _meds())
    assert decision.outcome == pipeline.ANSWERED and decision.intent == intent.WHEN
