"""Question type detection (T4_INPUTS section 3, plus 6a fuzzy).

Spoken forms come first, formal forms only as backup. Intents are checked in the
order of `INTENT_KEYWORDS`; the first intent with any match wins, which is what
keeps "ಎಷ್ಟ್ ದಿನ" (days left) and "ಎಷ್ಟೊತ್ತಿಗೆ" (when) out of HOW_MANY.
The function signature is deliberately small so a model-based detector can be
swapped in behind `detect()` later.
"""

from rapidfuzz.fuzz import partial_ratio

from . import normalise

WHEN = "WHEN"
HOW_MANY = "HOW_MANY"
FOOD = "FOOD"
PURPOSE = "PURPOSE"
DAYS_LEFT = "DAYS_LEFT"
# Asking to change the medicine (more, less, stop, skip). Never answered from
# the prescription: the pipeline always refers these to the doctor.
CHANGE = "CHANGE"
UNKNOWN = "UNKNOWN"

# Fuzzy fallback (section 6a): loose matching for keywords of 4+ characters.
INTENT_FUZZY = 88
MIN_FUZZY_LENGTH = 4

# Priority order matters: the first intent that matches wins.
INTENT_KEYWORDS = (
    (
        # First: "can I increase the dose?" contains "dose"/"ಎಷ್ಟು" too, and must
        # not be read as a how-many question.
        CHANGE,
        (
            # Kannada
            "ಜಾಸ್ತಿ ಮಾಡ",
            "ಹೆಚ್ಚು ಮಾಡ",
            "ಕಮ್ಮಿ ಮಾಡ",
            "ಕಡಿಮೆ ಮಾಡ",
            "ನಿಲ್ಲಿಸ",
            "ನಿಲ್ಸ",
            "ಬಿಟ್ಟುಬಿಡ",
            "ಬಿಡಬಹುದಾ",
            "ಬಿಡ್ಬೋದಾ",
            "ಬಿಡಬಹುದು",
            "ಡಬಲ್",
            # A missed or doubled dose is also the doctor's call, never ours.
            "ಮರೆತ",
            "ಮರ್ತ",
            "ಮಿಸ್",
            "ಎರಡು ತಗೊಂಡ",
            "ಎರಡ್ ತಗೊಂಡ",
            "ಎರಡು ಸಲ ತಗೊಂಡ",
            # Kanglish
            "jaasti maad",
            "kammi maad",
            "nillis",
            "bidbahuda",
            # English
            "increase",
            "reduce",
            "stop",
            "skip",
            "double",
            "missed",
            "forgot",
        ),
    ),
    (
        DAYS_LEFT,
        (
            # Kannada. A bare "ದಿನ" is deliberately NOT a keyword: it also
            # appears in "ದಿನಕ್ಕೆ ಎಷ್ಟು ಮಾತ್ರೆ" (how many per day) and in
            # symptoms like "ಎರಡು ದಿನದಿಂದ ಜ್ವರ" (fever for two days).
            "ಎಷ್ಟ್ ದಿನ",
            "ಎಷ್ಟು ದಿನ",
            "ಇನ್ನೆಷ್ಟು ದಿನ",
            "ಇನ್ನೂ ಎಷ್ಟ್",
            "ಇನ್ನೂ ಎಷ್ಟು",
            "ಎಷ್ಟು ದಿವಸ",
            "ಎಷ್ಟ್ ದಿವಸ",
            "ದಿನ ಬಾಕಿ",
            "ದಿನ ಉಳಿ",
            "ಮುಗೀತು",
            "ಮುಗಿಯುತ್ತೆ",
            "ಮುಗಿ",
            "ಎಲ್ಲಿವರೆಗೂ",
            "ಎಲ್ಲಿವರೆಗೆ",
            # Kanglish
            "eshtu dina",
            "esht dina",
            "innestu dina",
            "eshtu divasa",
            "mugi",
            # English
            "how many days",
            "days left",
            "how long",
            "finish",
        ),
    ),
    (
        FOOD,
        (
            # Kannada
            "ಊಟ",
            "ತಿಂಡಿ",
            "ತಿಂದ್ಮೇಲೆ",
            "ತಿಂದ",
            "ತಿನ್ನೋಕೆ",
            "ಖಾಲಿ ಹೊಟ್ಟೆ",
            "ಹೊಟ್ಟೇಲಿ",
            # Kanglish
            "oota",
            "uta",
            "tindi",
            "tindmele",
            "khaali hotte",
            # English
            "food",
            "eat",
            "meal",
            "empty stomach",
            "before food",
            "after food",
        ),
    ),
    (
        WHEN,
        (
            # Kannada
            "ಯಾವಾಗ",
            "ಯಾವಾಗ್",
            "ಎಷ್ಟೊತ್ತಿಗೆ",
            "ಎಷ್ಟ್ ಹೊತ್ತಿಗೆ",
            "ಯಾವ್ ಟೈಮ್",
            "ಯಾವ ಟೈಮ್",
            "ಯಾವ ಹೊತ್ತು",
            "ಟೈಮ್",
            # "How many times a day?" is answered by the list of times, not by
            # the per-dose count (WHEN is checked before HOW_MANY).
            "ಎಷ್ಟು ಸಲ",
            "ಎಷ್ಟ್ ಸಲ",
            "ಎಷ್ಟು ಸರ್ತಿ",
            "ಎಷ್ಟ್ ಸರ್ತಿ",
            # Kanglish
            "yaavaga",
            "yavaga",
            "eshtottige",
            "yaav time",
            "time",
            # English
            "when",
            "what time",
            "how many times",
        ),
    ),
    (
        HOW_MANY,
        (
            # Kannada
            "ಎಷ್ಟ್",
            "ಎಷ್ಟು",
            "ಎಷ್ಟೊಂದು",
            "ಎಷ್ಟ್ ಮಾತ್ರೆ",
            # Kanglish
            "eshtu",
            "estu",
            "esht",
            # English
            "how many",
            "how much",
            "dose",
        ),
    ),
    (
        PURPOSE,
        (
            # Kannada
            "ಯಾಕೆ",
            "ಯಾಕ್",
            "ಯಾತಕ್ಕೆ",
            "ಏತಕ್ಕೆ",
            "ಏನಕ್ಕೆ",
            "ಯಾವ್ದಕ್ಕೆ",
            "ಯಾವುದಕ್ಕೆ",
            "ಏನ್ ಮಾತ್ರೆ",
            "ಏನು ಮಾತ್ರೆ",
            # Kanglish
            "yaake",
            "yake",
            "yaatakke",
            "yenakke",
            "yaavdakke",
            "yen maatre",
            # English
            "why",
            "what for",
            "what is it for",
        ),
    ),
    (
        # Last resort for WHEN: a bare time of day ("ರಾತ್ರಿ ತಗೋಬೇಕಾ?" = "should I
        # take it at night?"). Checked after every other intent, so "ರಾತ್ರಿ ಎಷ್ಟು"
        # still counts as HOW_MANY. The WHEN answer lists all the times, which
        # answers the yes/no question too.
        WHEN,
        (
            "ಬೆಳಿಗ್ಗೆ",
            "ಬೆಳಗ್ಗೆ",
            "ಮಧ್ಯಾಹ್ನ",
            "ಸಂಜೆ",
            "ರಾತ್ರಿ",
            "beligge",
            "madhyana",
            "raatri",
            "rathri",
            "morning",
            "afternoon",
            "night",
        ),
    ),
)

# Normalised once at import so every request compares like with like.
_KEYWORDS = tuple(
    (intent, tuple(normalise(keyword) for keyword in keywords))
    for intent, keywords in INTENT_KEYWORDS
)

# The order T4_INPUTS asks for, exposed so tests and later code read the same list.
INTENTS = tuple(dict.fromkeys(intent for intent, _ in INTENT_KEYWORDS))


def _exact(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _fuzzy(text: str, keywords: tuple[str, ...]) -> bool:
    # A keyword longer than the whole transcript is never matched as a fragment
    # (partial_ratio would slide the transcript along it; see safety.py).
    return any(
        len(keyword) >= MIN_FUZZY_LENGTH
        and len(text) >= len(keyword)
        and partial_ratio(keyword, text) >= INTENT_FUZZY
        for keyword in keywords
    )


def detect(transcript: str) -> str:
    """Return one of CHANGE, WHEN, HOW_MANY, FOOD, PURPOSE, DAYS_LEFT or UNKNOWN."""
    text = normalise(transcript)
    if not text:
        return UNKNOWN
    for intent, keywords in _KEYWORDS:
        if _exact(text, keywords):
            return intent
    # Nothing matched exactly: try the softer comparison in the same order.
    for intent, keywords in _KEYWORDS:
        if _fuzzy(text, keywords):
            return intent
    return UNKNOWN
