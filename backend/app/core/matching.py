"""PROTECTED FILE: matches a transcript against the profile's confirmed medicines.

Two tablets can share a colour ("white tablet"), so matching may end in one
medicine, an ambiguous group, or nothing. Only `confirmed = true` rows are ever
candidates: the elder must never hear about a medicine the caregiver has not
checked. Thresholds are constants at the top so they can be tuned in one place.
"""

from dataclasses import dataclass, field

from rapidfuzz.fuzz import partial_ratio

from ..models import Medicine
from . import normalise

# Section 8: best score at least 80, and 10 points clear of the runner-up.
MIN_SCORE = 80
MIN_MARGIN = 10

# One colour word is stored in Kannada script; the Roman form lives in aliases so
# a caregiver does not have to type it twice (T4_INPUTS section 4).
COLOUR_WORDS = {
    "ಬಿಳಿ": "bili",
    "ಹಳದಿ": "haladi",
    "ಕೆಂಪು": "kempu",
    "ನೀಲಿ": "neeli",
    "ಹಸಿರು": "hasiru",
    "ಕಿತ್ತಳೆ": "kittale",
    "ಗುಲಾಬಿ": "gulabi",
    "ಕಪ್ಪು": "kappu",
    "ಕಂದು": "kandu",
}


# Words that mean "tablet/medicine" in general. Almost every question and many
# labels contain one, so they are removed before scoring; otherwise "ಈ ಬಿಳಿ
# ಮಾತ್ರೆ" scores ~91 against the alias "ಬಿಪಿ ಮಾತ್ರೆ" and two different tablets
# look tied. A field made only of these words is kept as-is.
GENERIC_WORDS = frozenset(
    normalise(word)
    for word in (
        "ಮಾತ್ರೆ", "ಮಾತ್ರೆಯ", "ಮಾತ್ರೆಗಳು", "ಗುಳಿಗೆ", "ಟ್ಯಾಬ್ಲೆಟ್", "ಟ್ಯಾಬ್ಲೆಟ್ಸ್", "ಕ್ಯಾಪ್ಸೂಲ್",
        "maatre", "matre", "tablet", "tablets", "pill", "pills", "capsule",
    )
)


def _without_generic(text: str) -> str:
    kept = [word for word in text.split() if word not in GENERIC_WORDS]
    return " ".join(kept) if kept else text


def with_colour_alias(aliases: list[str], color_word: str) -> list[str]:
    """Add the Roman form of a Kannada colour word to the aliases, once."""
    roman = COLOUR_WORDS.get((color_word or "").strip())
    cleaned = [alias.strip() for alias in aliases if alias and alias.strip()]
    if roman and roman not in (alias.lower() for alias in cleaned):
        cleaned.append(roman)
    return cleaned


@dataclass(frozen=True)
class MatchResult:
    """One medicine, an ambiguous shortlist, or neither."""

    medicine: Medicine | None = None
    candidates: tuple[Medicine, ...] = field(default_factory=tuple)
    # The elder named a colour that no confirmed medicine has ("the orange
    # tablet"): that tablet is not on the confirmed list, so nothing may be
    # answered about it, not even via the one-medicine fallback.
    unlisted: bool = False

    @property
    def ambiguous(self) -> bool:
        return self.medicine is None and len(self.candidates) > 1

    @property
    def found(self) -> bool:
        return self.medicine is not None


def _fields(medicine: Medicine, *, with_colour: bool = True) -> list[str]:
    """Every way the elder might refer to this medicine, normalised."""
    values = [medicine.name, medicine.label, *medicine.aliases]
    if with_colour:
        values.append(medicine.color_word)
    return [
        _without_generic(value)
        for value in (normalise(item) for item in values if item)
        if value
    ]


def _best(text: str, values: list[str]) -> float:
    return max((partial_ratio(value, text) for value in values), default=0.0)


def score(transcript: str, medicine: Medicine) -> float:
    """How close the (already normalised) transcript is to this medicine."""
    return _best(transcript, _fields(medicine))


def _scores(text: str, medicine: Medicine) -> tuple[float, float]:
    """(best over all fields, best ignoring the colour word).

    Two white tablets both score 100 on "ಬಿಳಿ"; the second number lets
    "ದೊಡ್ಡ ಬಿಳಿ" (the big white one) pick the right tablet by its label.
    """
    return _best(text, _fields(medicine)), _best(text, _fields(medicine, with_colour=False))


def _colours_in(text: str) -> set[str]:
    """Kannada colour words mentioned in the text (Kannada or Roman spelling)."""
    words = set(text.split())
    return {
        kannada
        for kannada, roman in COLOUR_WORDS.items()
        if normalise(kannada) in text or roman in words
    }


def _close(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Too close to call: neither number separates them.

    The label-only number counts only when it is a real match (>= MIN_SCORE);
    a weak 75 vs 57 is noise, not a reason to pick one white tablet over another.
    """
    if a[0] - b[0] >= MIN_MARGIN:
        return False
    if a[1] >= MIN_SCORE and a[1] - b[1] >= MIN_MARGIN:
        return False
    return True


def match(transcript: str, medicines: list[Medicine]) -> MatchResult:
    """Pick the medicine the elder meant, or report that it is unclear."""
    # Defence in depth: the pipeline already passes confirmed rows only.
    confirmed = [medicine for medicine in medicines if medicine.confirmed]
    if not confirmed:
        return MatchResult()

    text = _without_generic(normalise(transcript))
    if not text:
        return MatchResult()

    scored = sorted(
        ((_scores(text, medicine), medicine) for medicine in confirmed),
        key=lambda item: item[0],
        reverse=True,
    )
    top, top_medicine = scored[0]

    known_colours = {medicine.color_word for medicine in confirmed}
    unlisted = bool(_colours_in(text) - known_colours)

    if top[0] < MIN_SCORE:
        if unlisted:
            return MatchResult(unlisted=True)
        # Section 8: with exactly one confirmed medicine, anything is about it.
        if len(confirmed) == 1:
            return MatchResult(medicine=confirmed[0])
        return MatchResult()

    tied = tuple(
        medicine for value, medicine in scored if value[0] >= MIN_SCORE and _close(top, value)
    )
    if len(tied) > 1:
        return MatchResult(candidates=tied)

    return MatchResult(medicine=top_medicine)
