"""PROTECTED FILE: emergency detection (T4_INPUTS section 2, plus 6a fuzzy).

Checked before anything else in the pipeline. Any layer matching counts as an
emergency: a wrong alarm only shows the 108 message, while a missed emergency is
the failure we must avoid. New real-world phrasings go into the constants below,
not into new logic.
"""

from rapidfuzz.fuzz import partial_ratio

from . import normalise

# Fuzzy fallback (section 6a): keywords of 4+ characters are also compared
# loosely, so a misheard spelling still trips the alarm.
EMERGENCY_FUZZY = 85
MIN_FUZZY_LENGTH = 4

PHRASES_KANNADA = (
    "ಎದೆ ನೋವು",
    "ಎದೆನೋವು",
    "ಎದೆ ಭಾರ",
    "ಎದೆ ಹಿಡ್ಕೊಂಡ",
    "ಎದೆ ಹಿಡಿದುಕೊಂಡ",
    "ಉಸಿರು ಕಟ್ಟ",
    "ಉಸಿರು ಕಟ್ತಾ",
    "ಉಸಿರಾಡಕ್ಕೆ ಆಗ್ತಿಲ್ಲ",
    "ಉಸಿರು ತಗೊಳ್ಳಕ್ಕೆ ಆಗ್ತಿಲ್ಲ",
    "ದಮ್ ಕಟ್ಟ",
    "ಎಚ್ಚರ ತಪ್ಪ",
    "ಪ್ರಜ್ಞೆ ತಪ್ಪ",
    "ಪ್ರಜ್ಞೆ ಇಲ್ಲ",
    "ತಲೆ ತಿರುಗಿ ಬಿದ್ದ",
    "ಬಿದ್ಬಿಟ್ರು",
    "ಬಿದ್ದುಬಿಟ್ಟ",
    "ಮೂರ್ಛೆ",
    "ಫಿಟ್ಸ್",
    "ರಕ್ತ ಬರ್ತಿದೆ",
    "ರಕ್ತ ವಾಂತಿ",
    "ಮಾತು ಬರ್ತಿಲ್ಲ",
    "ಕೈ ಕಾಲು ಆಡ್ತಿಲ್ಲ",
    "ಜಾಸ್ತಿ ಮಾತ್ರೆ ತಗೊಂಡ್",
    "ತುಂಬಾ ಮಾತ್ರೆ ತಗೊಂಡ್",
    "ಎಲ್ಲಾ ಮಾತ್ರೆ ತಗೊಂಡ್",
)

# English words as Prisma writes them: in Kannada script.
PHRASES_ENGLISH_IN_KANNADA_SCRIPT = (
    "ಚೆಸ್ಟ್ ಪೇನ್",
    "ಹಾರ್ಟ್ ಅಟ್ಯಾಕ್",
    "ಬ್ರೀದಿಂಗ್",
    "ಸ್ಟ್ರೋಕ್",
    "ಓವರ್ ಡೋಸ್",
    "ಓವರ್‌ಡೋಸ್",
    "ಅನ್‌ಕಾನ್ಶಿಯಸ್",
    "ಫೇಂಟ್",
)

PHRASES_KANGLISH = (
    "ede novu",
    "edhe novu",
    "ede bhaara",
    "usiru katti",
    "usiru kattide",
    "usiradakke aagtilla",
    "dum katti",
    "eccara tappi",
    "prajne tappi",
    "bidbitru",
    "murche",
    "moorche",
    "fits",
    "rakta vaanti",
    "maatu bartilla",
    "jaasti maatre",
    "thumba maatre",
)

PHRASES_ENGLISH = (
    "chest pain",
    "heart attack",
    "can't breathe",
    "cannot breathe",
    "breathing problem",
    "unconscious",
    "fainted",
    "seizure",
    "stroke",
    "bleeding",
    "overdose",
    "too many tablets",
    "too many pills",
)

# Word pairs (section 2b): every group must match, any alternative inside a
# group is enough. Stems are substrings, so "ನೋವು"/"ನೋವಿದೆ" both hit "ನೋವ".
WORD_PAIRS = tuple(
    tuple(tuple(normalise(stem) for stem in group) for group in pair)
    for pair in (
        (("ಎದೆ",), ("ನೋವ", "ಭಾರ", "ಹಿಡ")),
        (("ಉಸಿರ",), ("ಕಷ್ಟ", "ಕಟ್ಟ", "ಆಗ್ತಿಲ್ಲ", "ಆಗುತ್ತಿಲ್ಲ", "ತೊಂದರೆ")),
        (("ಮಾತ್ರೆ",), ("ಜಾಸ್ತಿ", "ತುಂಬಾ", "ಎಲ್ಲಾ"), ("ತಗೊಂಡ", "ತೆಗೆದುಕೊಂಡ", "ನುಂಗ")),
    )
)

PHRASES = tuple(
    normalise(phrase)
    for phrase in (
        *PHRASES_KANNADA,
        *PHRASES_ENGLISH_IN_KANNADA_SCRIPT,
        *PHRASES_KANGLISH,
        *PHRASES_ENGLISH,
    )
)


def _pair_matches(text: str) -> bool:
    return any(
        all(any(stem in text for stem in group) for group in pair) for pair in WORD_PAIRS
    )


def _phrase_matches(text: str) -> bool:
    return any(phrase in text for phrase in PHRASES)


def _fuzzy_matches(text: str) -> bool:
    return any(
        len(phrase) >= MIN_FUZZY_LENGTH and partial_ratio(phrase, text) >= EMERGENCY_FUZZY
        for phrase in PHRASES
    )


def check(transcript: str) -> bool:
    """True if the transcript describes a possible emergency."""
    text = normalise(transcript)
    if not text:
        return False
    return _pair_matches(text) or _phrase_matches(text) or _fuzzy_matches(text)
