"""Regression: a lone word from an emergency phrase must not raise the alarm.

Seen live on 10 Nov: Prisma heard only "ಮಾತ್ರೆ" and the app showed 108, because
the fuzzy check slid the short transcript along "ಜಾಸ್ತಿ ಮಾತ್ರೆ ತಗೊಂಡ್".
"""

import pytest

from app.core import safety

NOT_EMERGENCIES = [
    "ಮಾತ್ರೆ", "ಮಾತ್ರೆ.", "ಮಾತ್ರೆ ತಗೊಂಡೆ", "ಎದೆ", "ಉಸಿರು", "ನೋವು", "ತಗೊಂಡ್",
    "ಗುಂಡು ಮಾತ್ರೆ ನುಂಗಕ್ಕೆ ಆಗಲ್ಲ", "ನನಗೆ ತಲೆ ನೋವು, ಯಾವ ಮಾತ್ರೆ ತಗೊಳ್ಳಲಿ?",
    "ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?", "ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ.", "ಗೊತ್ತಿದೆ.", "ಬೇಕು.",
]

EMERGENCIES = [
    "ಉಸಿರಾಡಲು ಆಗುತ್ತಿಲ್ಲ.", "ಎದೆ ನೋವು ಆಗ್ತಾ ಇದೆ.", "ಉಸಿರಾಡೋಕೆ ಕಷ್ಟ ಆಗ್ತಿದೆ",
    "ಚೆಸ್ಟ್ ಪೇನ್ ಆಗ್ತಿದೆ", "ಜಾಸ್ತಿ ಮಾತ್ರೆ ತಗೊಂಡ್ಬಿಟ್ಟೆ", "ತಲೆ ಸುತ್ತಿ ಬಿದ್ದುಬಿಟ್ಟೆ",
    "ಕೈ ಕಾಲು ಆಡ್ತಿಲ್ಲ", "ತುಂಬಾ ಉಸಿರು ಕಟ್ತಾ ಇದೆ", "ಎದೆ ಹತ್ರ ಒತ್ತಿದ ಹಾಗೆ ಆಗ್ತಿದೆ",
    "ಎದೆನೋವ", "ಮೂರ್ಚೆ ಬಂತು",
]


@pytest.mark.parametrize("text", NOT_EMERGENCIES)
def test_fragment_is_not_an_emergency(text):
    assert not safety.check(text)


@pytest.mark.parametrize("text", EMERGENCIES)
def test_real_emergency_still_caught(text):
    assert safety.check(text)
