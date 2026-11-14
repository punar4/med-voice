"""The /ask flow (section 7 of the task list, plus T4_INPUTS section 6).

    audio -> (convert) -> Prisma -> safety -> intent -> matching
          -> follow-up rules -> answer template -> Timbre -> QuestionLog

`decide()` is pure (no network, no database) so every rule can be unit-tested;
`run()` wires it to Gnani and the database.

Outcome order, first rule that applies wins:
1. emergency words                       -> emergency (always, before anything else)
   asking to change the dose / stop       -> referral
2. two tablets match equally well        -> clarify_which
   a colour no confirmed tablet has      -> referral
3. follow-ups within FOLLOWUP_SECONDS of the previous question (section 6b),
   including a tablet-less question right after an answer about a tablet
4. tablet known, question unknown        -> clarify_question once, then referral
5. question unknown, tablet unknown      -> referral
6. question known, tablet unknown        -> clarify_repeat
7. both known                            -> answered, or referral if the
   caregiver left that field empty / the course is over
"""

import base64
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from .. import audio
from ..gnani import GnaniNotConfigured, stt, tts
from ..models import Medicine, Profile, QuestionLog
from . import answers, intent, matching, normalise, safety
from .matching import COLOUR_WORDS

logger = logging.getLogger(__name__)

# A question this soon after the previous one may be a follow-up ("ಯಾವಾಗ?").
FOLLOWUP_SECONDS = 120

# India has no daylight saving, so a fixed offset is exact (and avoids needing
# the tzdata package on Windows).
IST = timezone(timedelta(hours=5, minutes=30))

# Words always worth boosting in Prisma, on top of the elder's own medicine words.
FIXED_KEYTERMS = ("ಮಾತ್ರೆ", "ಊಟ", "ಯಾವಾಗ", "ಎಷ್ಟು")

ANSWERED = "answered"
CLARIFY_WHICH = "clarify_which"
CLARIFY_QUESTION = "clarify_question"
CLARIFY_REPEAT = "clarify_repeat"
REFERRAL = "referral"
EMERGENCY = "emergency"
ERROR = "error"

INTENT_TEMPLATE = {
    intent.WHEN: "when",
    intent.HOW_MANY: "how_many",
    intent.FOOD: "food",
    intent.PURPOSE: "purpose",
    intent.DAYS_LEFT: "days_left",
}


@dataclass
class Decision:
    outcome: str
    answer_key: str
    intent: str
    medicine: Medicine | None = None
    fields: dict = field(default_factory=dict)


def _referral(question: str, medicine: Medicine | None = None) -> Decision:
    return Decision(REFERRAL, "referral", question, medicine)


def today_ist() -> date:
    return datetime.now(IST).date()


def _answer(question: str, medicine: Medicine, lang: str, today: date) -> Decision:
    """Fill the answer for a known question about a known tablet, or refer."""
    label = medicine.label
    if question == intent.WHEN:
        if not medicine.times:
            return _referral(question, medicine)
        fields = {"label": label, "times": answers.times_phrase(medicine.times, lang)}
    elif question == intent.HOW_MANY:
        fields = {"label": label, "dose": medicine.dose}
    elif question == intent.FOOD:
        fields = {"label": label, "food": answers.food_phrase(medicine.food or "any", lang)}
    elif question == intent.PURPOSE:
        if not (medicine.purpose or "").strip():
            return _referral(question, medicine)
        fields = {"label": label, "purpose": medicine.purpose.strip()}
    elif question == intent.DAYS_LEFT:
        if not medicine.days_total or not medicine.start_date:
            return _referral(question, medicine)
        left = medicine.days_total - (today - medicine.start_date).days
        if left <= 0:
            # Course over (or dates wrong): whether to continue is the doctor's call.
            return _referral(question, medicine)
        fields = {"label": label, "days": left}
    else:
        return _referral(question, medicine)
    return Decision(ANSWERED, INTENT_TEMPLATE[question], question, medicine, fields)


def decide(
    transcript: str,
    medicines: list[Medicine],
    previous: QuestionLog | None = None,
    *,
    lang: str = "kn",
    now: datetime | None = None,
    today: date | None = None,
) -> Decision:
    """Pick what to say. `previous` is the profile's latest QuestionLog row."""
    now = now or datetime.now(timezone.utc)
    today = today or today_ist()

    if safety.check(transcript):
        return Decision(EMERGENCY, "emergency_108", intent.UNKNOWN)

    confirmed = [medicine for medicine in medicines if medicine.confirmed]
    question = intent.detect(transcript)
    result = matching.match(transcript, confirmed)

    if question == intent.CHANGE:
        # More, less, stop, skip: only the doctor decides, whichever tablet.
        return _referral(question, result.medicine)

    if result.ambiguous:
        options = answers.join_or([medicine.label for medicine in result.candidates], lang)
        return Decision(CLARIFY_WHICH, "clarify_which", question, fields={"options": options})

    if result.unlisted:
        # e.g. "the orange tablet" when only a white one is confirmed.
        return _referral(question)

    medicine = result.medicine
    recent = _recent(previous, now)

    # 6b rule 3: "ಬಿಳಿ" after "which tablet?" (or a tablet name after "say its
    # colour or name") keeps the question asked before.
    if (
        medicine is not None
        and question == intent.UNKNOWN
        and recent is not None
        and recent.outcome in (CLARIFY_WHICH, CLARIFY_REPEAT)
        and recent.intent != intent.UNKNOWN
    ):
        question = recent.intent

    # 6b rule 2: just "ಯಾವಾಗ?" after "what about this tablet?" keeps the tablet,
    # and so does a short follow-up ("ಎಷ್ಟು ತಗೋಬೇಕು?") right after an answer about
    # it. Safe because every answer starts by naming the tablet it is about.
    # (With one confirmed medicine, matching already picked it.)
    if medicine is None and question != intent.UNKNOWN and recent is not None and not _means_another(transcript):
        if recent.outcome in (CLARIFY_QUESTION, ANSWERED) and recent.medicine_id is not None:
            medicine = next((m for m in confirmed if m.id == recent.medicine_id), None)

    if medicine is not None and question == intent.UNKNOWN:
        # 6b rule 1: ask back once; a second unclear question gets a referral.
        if recent is not None and recent.outcome == CLARIFY_QUESTION:
            return _referral(question, medicine)
        return Decision(CLARIFY_QUESTION, "clarify_question", question, medicine, {"label": medicine.label})

    if medicine is None and question == intent.UNKNOWN:
        return _referral(question)

    if medicine is None:
        return Decision(CLARIFY_REPEAT, "clarify_repeat", question)

    return _answer(question, medicine, lang, today)


# "the other tablet" must never be answered with the tablet just discussed.
OTHER_TABLET_WORDS = frozenset({"ಇನ್ನೊಂದು", "ಮತ್ತೊಂದು", "ಬೇರೆ", "ಬೇರೇ", "other", "another", "different"})


def _means_another(transcript: str) -> bool:
    return any(word in OTHER_TABLET_WORDS for word in normalise(transcript).split())


def _recent(previous: QuestionLog | None, now: datetime) -> QuestionLog | None:
    if previous is None or previous.created_at is None:
        return None
    created = previous.created_at
    if created.tzinfo is None:  # SQLite hands back naive datetimes
        created = created.replace(tzinfo=timezone.utc)
    return previous if (now - created).total_seconds() <= FOLLOWUP_SECONDS else None


def keyterms_for(medicines: list[Medicine]) -> list[str]:
    """Words for Prisma to listen for: confirmed medicines only, plus fixed words."""
    terms: list[str] = []
    for medicine in medicines:
        if not medicine.confirmed:
            continue
        terms += [medicine.name, medicine.label, medicine.color_word, *medicine.aliases]
        roman = COLOUR_WORDS.get(medicine.color_word)
        if roman:
            terms.append(roman)
    terms += FIXED_KEYTERMS
    return list(dict.fromkeys(term.strip() for term in terms if term and term.strip()))


@dataclass
class AskResult:
    transcript: str
    outcome: str
    answer_text: str
    audio_base64: str | None
    medicine: dict | None
    audio_error: bool = False
    # The same answer in English, for caregivers and the English screen. Only
    # the Kannada one is spoken; tablet labels and doses stay as typed.
    answer_text_en: str = ""


def _confirmed(session: Session, profile: Profile) -> list[Medicine]:
    return list(
        session.exec(
            select(Medicine).where(Medicine.profile_id == profile.id, Medicine.confirmed == True)  # noqa: E712
        ).all()
    )


def _latest_log(session: Session, profile: Profile) -> QuestionLog | None:
    return session.exec(
        select(QuestionLog)
        .where(QuestionLog.profile_id == profile.id)
        .order_by(QuestionLog.created_at.desc(), QuestionLog.id.desc())
    ).first()


def run(session: Session, profile: Profile, audio_bytes: bytes) -> AskResult:
    """The whole /ask request: speech in, logged decision and speech out."""
    lang = profile.language or "kn"
    medicines = _confirmed(session, profile)

    try:
        if stt.config.MOCK_GNANI:
            clip, filename = audio_bytes, None  # mock mode never sends audio anywhere
        else:
            clip, filename = audio.prepare_for_prisma(audio_bytes)
        transcript = stt.transcribe(clip, lang, keyterms=keyterms_for(medicines), filename=filename)
    except (audio.AudioError, GnaniNotConfigured) as exc:
        logger.warning("could not transcribe: %s", exc)
        transcript = None

    if not transcript:
        # No speech, unreadable audio or Prisma down: ask again, and log it.
        decision = Decision(ERROR, "error_try_again", intent.UNKNOWN)
        decision_en = decision
        transcript = transcript or ""
    else:
        previous = _latest_log(session, profile)
        decision = decide(transcript, medicines, previous, lang=lang)
        # decide() is pure, so the English run reaches the same outcome.
        decision_en = decide(transcript, medicines, previous, lang="en")

    text = answers.render(decision.answer_key, lang, **decision.fields)
    try:
        text_en = answers.render(decision_en.answer_key, "en", **decision_en.fields)
    except answers.TemplateError:
        text_en = ""

    audio_b64, audio_error = None, False
    try:
        audio_b64 = base64.b64encode(tts.synthesize(text, lang)).decode("ascii")
    except GnaniNotConfigured as exc:
        # The text answer (and the 108 banner) still reach the screen.
        logger.warning("could not speak the answer: %s", exc)
        audio_error = True

    session.add(
        QuestionLog(
            profile_id=profile.id,
            transcript=transcript,
            intent=decision.intent,
            medicine_id=decision.medicine.id if decision.medicine else None,
            outcome=decision.outcome,
            answer_key=decision.answer_key,
            answer_text=text,
        )
    )
    session.commit()

    medicine = decision.medicine
    return AskResult(
        transcript=transcript,
        outcome=decision.outcome,
        answer_text=text,
        audio_base64=audio_b64,
        medicine={"label": medicine.label, "photo_url": medicine.photo_path} if medicine else None,
        audio_error=audio_error,
        answer_text_en=text_en,
    )
