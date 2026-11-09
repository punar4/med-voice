"""PROTECTED FILE: fills answer templates (section 8 of the task list).

Every sentence the elder hears comes from `templates/<lang>.json`, filled only
with caregiver-confirmed medicine fields. Nothing here writes medical content
of its own, does arithmetic on doses, or falls back to generated text: an
unknown template key is a bug and raises.

Do not change the rules or logic in this file without explicit human approval.
"""

import json
from functools import lru_cache
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

# Order in which times are spoken, whatever order the caregiver ticked them in.
TIME_ORDER = ("morning", "afternoon", "night")


class TemplateError(KeyError):
    """A template key or placeholder is missing: never paper over it."""


@lru_cache(maxsize=None)
def load(lang: str) -> dict[str, str]:
    """Read and cache one language's template file (e.g. kn.json)."""
    path = TEMPLATES_DIR / f"{lang}.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def word(key: str, lang: str) -> str:
    templates = load(lang)
    if key not in templates:
        raise TemplateError(f"template key {key!r} missing from {lang}.json")
    return templates[key]


def join_and(items: list[str], lang: str) -> str:
    """"A", "A ಮತ್ತೆ B", "A, B ಮತ್ತೆ C"."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} {word('join_and', lang)} {items[-1]}"


def join_or(items: list[str], lang: str) -> str:
    return f" {word('join_or', lang)} ".join(items)


def times_phrase(times: list[str], lang: str) -> str:
    ordered = [time for time in TIME_ORDER if time in set(times)]
    return join_and([word(f"time_{time}", lang) for time in ordered], lang)


def food_phrase(food: str, lang: str) -> str:
    return word(f"food_{food}", lang)


def render(key: str, lang: str, **fields: object) -> str:
    """Fill one template; a missing placeholder value raises instead of guessing."""
    template = word(key, lang)
    try:
        return template.format(**fields)
    except KeyError as exc:
        raise TemplateError(f"template {key!r} needs {exc.args[0]!r}") from None
