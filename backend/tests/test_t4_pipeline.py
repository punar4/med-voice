"""T4: safety, intent, matching, answers and the follow-up rules (T4_INPUTS_v4).

`pipeline.decide()` is pure, so these tests build Medicine/QuestionLog objects in
memory: no database, no network.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.core import answers, intent, pipeline, safety
from app.core.matching import match, with_colour_alias
from app.models import Medicine, QuestionLog

TODAY = date(2026, 11, 10)
NOW = datetime(2026, 11, 10, 6, 0, tzinfo=timezone.utc)


def med(id_, label, colour, **extra):
    fields = dict(
        id=id_,
        profile_id=1,
        name=extra.pop("name", f"Medicine {id_}"),
        aliases=extra.pop("aliases", []),
        label=label,
        color_word=colour,
        dose=extra.pop("dose", "1 ಮಾತ್ರೆ"),
        times=extra.pop("times", ["morning", "night"]),
        food=extra.pop("food", "after"),
        confirmed=extra.pop("confirmed", True),
    )
    fields.update(extra)
    return Medicine(**fields)


WHITE = med(1, "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ", "ಬಿಳಿ", name="Amlodipine 5mg",
            aliases=["BP tablet", "ಬಿಪಿ ಮಾತ್ರೆ"], purpose="ಬಿಪಿ ಮಾತ್ರೆ",
            days_total=30, start_date=TODAY - timedelta(days=5))
BIG_WHITE = med(2, "ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ", "ಬಿಳಿ", name="Metformin 500mg",
                aliases=["ಶುಗರ್ ಮಾತ್ರೆ"], times=["morning"])
YELLOW = med(3, "ಹಳದಿ ಮಾತ್ರೆ", "ಹಳದಿ", food="any", times=["afternoon"])
ORANGE_UNCONFIRMED = med(4, "ಉದ್ದ ಕಿತ್ತಳೆ ಮಾತ್ರೆ", "ಕಿತ್ತಳೆ", confirmed=False)


def decide(text, medicines, previous=None, now=NOW):
    return pipeline.decide(text, medicines, previous, now=now, today=TODAY)


def text_of(decision):
    return answers.render(decision.answer_key, "kn", **decision.fields)


def log(outcome, intent_, medicine_id=None, seconds_ago=30):
    return QuestionLog(
        profile_id=1, transcript="", intent=intent_, medicine_id=medicine_id,
        outcome=outcome, answer_key="", answer_text="",
        created_at=NOW - timedelta(seconds=seconds_ago),
    )


# --- The exact cases from T4_INPUTS_v4 section 5 ---------------------------

def test_live_prisma_transcript_answers_when():
    d = decide("ಈ ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?", [WHITE])
    assert d.outcome == "answered"
    assert text_of(d) == "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ. ಇದನ್ನ ಬೆಳಿಗ್ಗೆ ಮತ್ತೆ ರಾತ್ರಿ ತಗೊಳ್ಳಿ."


@pytest.mark.parametrize("text", [
    "ಎದೆ ನೋವು ಆಗ್ತಿದೆ, ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ?",   # beats a normal question
    "ಎದೆ ತುಂಬಾ ಭಾರ ಆಗ್ತಿದೆ",                  # pair rule
    "ಉಸಿರಾಡೋಕೆ ತುಂಬಾ ಕಷ್ಟ ಆಗ್ತಿದೆ",             # pair rule
    "ಅಮ್ಮ ಜಾಸ್ತಿ ಮಾತ್ರೆ ತಗೊಂಡ್ಬಿಟ್ರು",           # too many tablets
    "ಚೆಸ್ಟ್ ಪೇನ್ ಆಗ್ತಿದೆ",                     # English in Kannada script
    "chest pain aagtide",
])
def test_emergencies(text):
    assert decide(text, [WHITE, YELLOW]).outcome == "emergency"


@pytest.mark.parametrize("text", [
    "ಬಿಪಿ ಮಾತ್ರೆ ಯಾವಾಗ?",
    "ಈ ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?",
    "ದಿನಕ್ಕೆ ಎಷ್ಟು ಮಾತ್ರೆ ತಗೋಬೇಕು?",
    "ಊಟ ಆದ್ಮೇಲೆ ತಗೋಬೇಕಾ?",
    "ಇನ್ನೂ ಎಷ್ಟು ದಿನ ತಗೋಬೇಕು?",
    "ಹಳದಿ ಮಾತ್ರೆ ಯಾಕೆ?",
    "BP tablet yaavaga tegedukollabeku",
])
def test_ordinary_questions_are_not_emergencies(text):
    assert safety.check(text) is False


def test_days_left():
    d = decide("ಇನ್ನೂ ಎಷ್ಟು ದಿನ ತಗೋಬೇಕು?", [WHITE])
    assert d.outcome == "answered"
    assert text_of(d) == "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ. ಇನ್ನೂ 25 ದಿನ ತಗೋಬೇಕು."


def test_milk_question_asks_back_once_then_refers():
    first = decide("ಇದನ್ನ ಹಾಲಿನ ಜೊತೆ ತಗೋಬಹುದಾ?", [WHITE])
    assert first.outcome == "clarify_question"
    assert first.medicine is WHITE
    again = decide("ಇದನ್ನ ಹಾಲಿನ ಜೊತೆ ತಗೋಬಹುದಾ?", [WHITE], log("clarify_question", "UNKNOWN", 1))
    assert again.outcome == "referral"


def test_follow_up_question_uses_the_tablet_from_the_ask_back():
    first = decide("ಬಿಳಿ ಮಾತ್ರೆ ಬಗ್ಗೆ", [WHITE, YELLOW])
    assert first.outcome == "clarify_question"
    assert first.medicine is WHITE
    follow = decide("ಯಾವಾಗ?", [WHITE, YELLOW], log("clarify_question", "UNKNOWN", WHITE.id))
    assert follow.outcome == "answered"
    assert follow.medicine is WHITE


def test_two_white_tablets_then_pick_one():
    which = decide("ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ?", [WHITE, BIG_WHITE])
    assert which.outcome == "clarify_which"
    assert text_of(which) == "ಯಾವ ಮಾತ್ರೆ ಬಗ್ಗೆ ಕೇಳ್ತಾ ಇದ್ದೀರಿ? ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ ಅಥವಾ ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ?"
    picked = decide("ದೊಡ್ಡ ಬಿಳಿ", [WHITE, BIG_WHITE], log("clarify_which", "WHEN"))
    assert picked.outcome == "answered"
    assert picked.medicine is BIG_WHITE
    assert text_of(picked) == "ದೊಡ್ಡ ಬಿಳಿ ಮಾತ್ರೆ. ಇದನ್ನ ಬೆಳಿಗ್ಗೆ ತಗೊಳ್ಳಿ."


def test_misheard_when_still_understood():
    d = decide("ಯಾವಗ ತಗೋಬೇಕು ಬಿಳಿ ಮಾತ್ರೆ", [WHITE, YELLOW])
    assert d.outcome == "answered"
    assert d.intent == "WHEN"


# --- Safety of the medicine list ---------------------------------------------

def test_unconfirmed_medicine_is_never_matched():
    assert match("ಉದ್ದ ಕಿತ್ತಳೆ ಮಾತ್ರೆ", [ORANGE_UNCONFIRMED]).medicine is None


def test_asking_about_an_unconfirmed_colour_refers_instead_of_answering_another_tablet():
    # Only the white tablet is confirmed; the one-medicine fallback must not
    # answer a question about an orange tablet with the white tablet's details.
    d = decide("ಕಿತ್ತಳೆ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?", [WHITE, ORANGE_UNCONFIRMED])
    assert d.outcome == "referral"
    assert d.medicine is None


def test_generic_word_tablet_does_not_tie_different_tablets():
    # Before T4's fix, "ಬಿಪಿ ಮಾತ್ರೆ" scored ~91 against "ಬಿಳಿ ಮಾತ್ರೆ" just from "ಮಾತ್ರೆ".
    result = match("ಈ ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?", [WHITE, YELLOW])
    assert result.medicine is WHITE


# --- Intent edge cases found while building T4 ----------------------------------

@pytest.mark.parametrize("text, expected", [
    ("ದಿನಕ್ಕೆ ಎಷ್ಟು ಮಾತ್ರೆ ತಗೋಬೇಕು?", "HOW_MANY"),   # "per day" is not "days left"
    ("ಎರಡು ದಿನದಿಂದ ಜ್ವರ ಇದೆ", "UNKNOWN"),             # a symptom, not a question
    ("ರಾತ್ರಿ ತಗೋಬೇಕಾ?", "WHEN"),                       # yes/no about a time
    ("ರಾತ್ರಿ ಎಷ್ಟು ಮಾತ್ರೆ?", "HOW_MANY"),
    ("ಬಿಳಿ ಮಾತ್ರೆ ಎಷ್ಟೊತ್ತಿಗೆ ತಗೋಬೇಕು?", "WHEN"),
    ("ತಿಂದ್ಮೇಲೆ ತಗೋಬೇಕಾ?", "FOOD"),
    ("ಇದು ಏನು ಮಾತ್ರೆ?", "PURPOSE"),
])
def test_intent_edge_cases(text, expected):
    assert intent.detect(text) == expected


# --- Fallbacks -----------------------------------------------------------------

def test_known_question_unknown_tablet_asks_to_repeat():
    assert decide("ಯಾವಾಗ?", [WHITE, YELLOW]).outcome == "clarify_repeat"


def test_symptom_with_several_tablets_is_referred():
    assert decide("ಎರಡು ದಿನದಿಂದ ಜ್ವರ ಇದೆ", [WHITE, YELLOW]).outcome == "referral"


def test_purpose_only_if_written():
    assert text_of(decide("ಬಿಳಿ ಮಾತ್ರೆ ಯಾಕೆ?", [WHITE, YELLOW])).endswith("ಇದು ಬಿಪಿ ಮಾತ್ರೆ.")
    assert decide("ಹಳದಿ ಮಾತ್ರೆ ಯಾಕೆ?", [WHITE, YELLOW]).outcome == "referral"


def test_course_finished_is_referred():
    old = med(9, "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ", "ಬಿಳಿ", days_total=3, start_date=TODAY - timedelta(days=10))
    assert decide("ಇನ್ನೂ ಎಷ್ಟು ದಿನ?", [old]).outcome == "referral"


def test_food_any_and_how_many():
    assert text_of(decide("ಹಳದಿ ಮಾತ್ರೆ ಊಟಕ್ಕೆ ಮುಂಚೆನಾ?", [WHITE, YELLOW])) == \
        "ಹಳದಿ ಮಾತ್ರೆ. ಇದನ್ನ ಊಟಕ್ಕೆ ಮುಂಚೆ ಆದ್ರೂ, ಆದ್ಮೇಲೆ ಆದ್ರೂ ತಗೊಳ್ಳಿ."
    assert text_of(decide("ದಿನಕ್ಕೆ ಎಷ್ಟು ಬಿಳಿ ಮಾತ್ರೆ?", [WHITE, YELLOW])) == \
        "ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ. ಒಂದ್ ಸಲಕ್ಕೆ 1 ಮಾತ್ರೆ ತಗೊಳ್ಳಿ."


def test_old_previous_question_is_not_a_follow_up():
    stale = log("clarify_question", "UNKNOWN", WHITE.id, seconds_ago=pipeline.FOLLOWUP_SECONDS + 5)
    assert decide("ಯಾವಾಗ?", [WHITE, YELLOW], stale).outcome == "clarify_repeat"


# --- Templates and helpers -------------------------------------------------------

def test_every_template_key_used_by_the_pipeline_exists():
    keys = set(answers.load("kn"))
    used = set(pipeline.INTENT_TEMPLATE.values()) | {
        "clarify_which", "clarify_question", "clarify_repeat", "referral",
        "emergency_108", "error_try_again", "join_and", "join_or",
        "time_morning", "time_afternoon", "time_night", "food_before", "food_after", "food_any",
    }
    assert used <= keys


def test_unknown_template_key_raises():
    with pytest.raises(answers.TemplateError):
        answers.render("no_such_key", "kn")


def test_three_times_joined_naturally():
    assert answers.times_phrase(["night", "morning", "afternoon"], "kn") == "ಬೆಳಿಗ್ಗೆ, ಮಧ್ಯಾಹ್ನ ಮತ್ತೆ ರಾತ್ರಿ"


def test_colour_alias_added_once():
    assert with_colour_alias(["BP tablet"], "ಬಿಳಿ") == ["BP tablet", "bili"]
    assert with_colour_alias(["bili"], "ಬಿಳಿ") == ["bili"]


def test_keyterms_use_confirmed_medicines_only():
    terms = pipeline.keyterms_for([WHITE, ORANGE_UNCONFIRMED])
    assert "Amlodipine 5mg" in terms and "bili" in terms and "ಮಾತ್ರೆ" in terms
    assert "ಉದ್ದ ಕಿತ್ತಳೆ ಮಾತ್ರೆ" not in terms


def test_hard_to_swallow_is_not_an_overdose():
    # "ನುಂಗಕ್ಕೆ ಆಗಲ್ಲ" (can't swallow) must not trip the "swallowed too many" pair.
    assert safety.check("ಈ ಮಾತ್ರೆ ತುಂಬಾ ದೊಡ್ಡದು ನುಂಗಕ್ಕೆ ಆಗಲ್ಲ") is False
    assert safety.check("ಅವರು ತುಂಬಾ ಮಾತ್ರೆ ನುಂಗಿಬಿಟ್ರು") is True
