"""Shared text helper for safety, intent and matching.

Prisma (prisma-v3.0, format codemix, kn-IN) writes a spoken Kanglish question in
Kannada script, so every matcher works on one normalised form: Unicode NFC,
lowercase (affects Roman/English only), punctuation stripped, spaces collapsed.
Kannada letters, vowel signs and the virama are kept on purpose; dropping the
marks would cut words into fragments that no keyword could match.
"""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def _is_kept(char: str) -> bool:
    """True for letters (incl. Kannada), combining marks (vowel signs, virama), digits and spaces."""
    if char.isspace():
        return True
    return unicodedata.category(char)[0] in {"L", "M", "N"}


def normalise(text: str) -> str:
    """Return the single form used for every keyword comparison in this package."""
    prepared = unicodedata.normalize("NFC", text or "").lower()
    cleaned = "".join(char if _is_kept(char) else " " for char in prepared)
    return _WHITESPACE.sub(" ", cleaned).strip()
