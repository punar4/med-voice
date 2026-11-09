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


@dataclass(frozen=True)
class MatchResult:
    """One medicine, an ambiguous shortlist, or neither."""

    medicine: Medicine | None = None
    candidates: tuple[Medicine, ...] = field(default_factory=tuple)

    @property
    def ambiguous(self) -> bool:
        return self.medicine is None and len(self.candidates) > 1

    @property
    def found(self) -> bool:
        return self.medicine is not None


def _fields(medicine: Medicine) -> list[str]:
    """Every way the elder might refer to this medicine, normalised."""
    values = [medicine.name, medicine.label, medicine.color_word, *medicine.aliases]
    return [value for value in (normalise(item) for item in values if item) if value]


def score(transcript: str, medicine: Medicine) -> float:
    """How close the (already normalised) transcript is to this medicine."""
    return max(
        (partial_ratio(value, transcript) for value in _fields(medicine)),
        default=0.0,
    )


def match(transcript: str, medicines: list[Medicine]) -> MatchResult:
    """Pick the medicine the elder meant, or report that it is unclear."""
    # Defence in depth: the pipeline already passes confirmed rows only.
    confirmed = [medicine for medicine in medicines if medicine.confirmed]
    if not confirmed:
        return MatchResult()

    text = normalise(transcript)
    if not text:
        return MatchResult()

    scored = sorted(
        ((score(text, medicine), medicine) for medicine in confirmed),
        key=lambda item: item[0],
        reverse=True,
    )
    top_score, top_medicine = scored[0]

    if top_score < MIN_SCORE:
        # Section 8: with exactly one confirmed medicine, anything is about it.
        if len(confirmed) == 1:
            return MatchResult(medicine=confirmed[0])
        return MatchResult()

    second_score = scored[1][0] if len(scored) > 1 else 0.0
    if second_score >= MIN_SCORE and top_score - second_score < MIN_MARGIN:
        tied = tuple(
            medicine
            for value, medicine in scored
            if value >= MIN_SCORE and top_score - value < MIN_MARGIN
        )
        return MatchResult(candidates=tied)

    return MatchResult(medicine=top_medicine)
