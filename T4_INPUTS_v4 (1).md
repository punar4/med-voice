# T4_INPUTS.md (v4) — human-approved inputs for T4

Read this together with FREEBUFF_TASKS_v4.md before T4. Everything here was written by the human (with Claude) and verified; use it exactly. Do not invent extra words.

## 0. Key finding from the live Prisma test

Prisma (prisma-v3.0, format codemix, kn-IN) returned the spoken Kanglish question
"ee bili maatre yaavaga tagobeku?" as **Kannada script**: `ಈ ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?`
So every keyword list below is matched mainly in **Kannada script**, with Roman (Kanglish) and English forms as backup.

Normalisation before matching (safety, intent, matching): Unicode NFC, lowercase (affects Roman/English only), strip punctuation (keep Kannada letters, vowel signs and virama), collapse spaces. Match by substring on the normalised text.

**Language rule for this whole project: spoken, colloquial Kannada everywhere** (what elders actually say and understand), not formal written Kannada. Templates are written in spoken form (ತಗೊಳ್ಳಿ, not ತೆಗೆದುಕೊಳ್ಳಿ); keyword lists list spoken forms first, formal forms only as backup.

## 1. Templates

Replace `backend/app/templates/kn.json` with the contents of the provided `kn_v2.json` exactly (keep the file name kn.json) (it is a protected file; this is the human-provided version).

- `{times}`: join the `time_*` words with `join_and` (e.g. ಬೆಳಿಗ್ಗೆ ಮತ್ತೆ ರಾತ್ರಿ). Three items: "A, B ಮತ್ತೆ C".
- `{food}`: the matching `food_*` value.
- `{options}` in `clarify_which`: the candidate labels joined with `join_or`.
- `{dose}`, `{purpose}`, `{label}`: the caregiver-confirmed values, inserted as-is.
- `{days}`: an integer.
- New keys versus the T0 placeholder file: `join_and`, `join_or`, `clarify_question` (section 6b).

## 2. Emergency detection (safety.py, checked first)

Elders speak colloquial Kannada, often mixed with English words that Prisma writes in Kannada script. So emergency detection uses three layers. **Any layer matching = emergency.** It deliberately errs on the side of safety: a false alarm only shows the 108 message; a missed emergency is the failure we must avoid.

### 2a. Phrases (substring match)

Spoken Kannada script:
ಎದೆ ನೋವು, ಎದೆನೋವು, ಎದೆ ಭಾರ, ಎದೆ ಹಿಡ್ಕೊಂಡ, ಎದೆ ಹಿಡಿದುಕೊಂಡ, ಉಸಿರು ಕಟ್ಟ, ಉಸಿರು ಕಟ್ತಾ, ಉಸಿರಾಡಕ್ಕೆ ಆಗ್ತಿಲ್ಲ, ಉಸಿರು ತಗೊಳ್ಳಕ್ಕೆ ಆಗ್ತಿಲ್ಲ, ದಮ್ ಕಟ್ಟ, ಎಚ್ಚರ ತಪ್ಪ, ಪ್ರಜ್ಞೆ ತಪ್ಪ, ಪ್ರಜ್ಞೆ ಇಲ್ಲ, ತಲೆ ತಿರುಗಿ ಬಿದ್ದ, ಬಿದ್ಬಿಟ್ರು, ಬಿದ್ದುಬಿಟ್ಟ, ಮೂರ್ಛೆ, ಫಿಟ್ಸ್, ರಕ್ತ ಬರ್ತಿದೆ, ರಕ್ತ ವಾಂತಿ, ಮಾತು ಬರ್ತಿಲ್ಲ, ಕೈ ಕಾಲು ಆಡ್ತಿಲ್ಲ, ಜಾಸ್ತಿ ಮಾತ್ರೆ ತಗೊಂಡ್, ತುಂಬಾ ಮಾತ್ರೆ ತಗೊಂಡ್, ಎಲ್ಲಾ ಮಾತ್ರೆ ತಗೊಂಡ್

English words as Prisma writes them in Kannada script:
ಚೆಸ್ಟ್ ಪೇನ್, ಹಾರ್ಟ್ ಅಟ್ಯಾಕ್, ಬ್ರೀದಿಂಗ್, ಸ್ಟ್ರೋಕ್, ಓವರ್ ಡೋಸ್, ಓವರ್‌ಡೋಸ್, ಅನ್‌ಕಾನ್ಶಿಯಸ್, ಫೇಂಟ್

Kanglish (Roman):
ede novu, edhe novu, ede bhaara, usiru katti, usiru kattide, usiradakke aagtilla, dum katti, eccara tappi, prajne tappi, bidbitru, murche, moorche, fits, rakta vaanti, maatu bartilla, jaasti maatre, thumba maatre

English:
chest pain, heart attack, can't breathe, cannot breathe, breathing problem, unconscious, fainted, seizure, stroke, bleeding, overdose, too many tablets, too many pills

### 2b. Word pairs (both stems present anywhere in the transcript)

- ಎದೆ + (ನೋವ, ಭಾರ, ಹಿಡ)  → chest + pain/heaviness/tightness
- ಉಸಿರ + (ಕಷ್ಟ, ಕಟ್ಟ, ಆಗ್ತಿಲ್ಲ, ಆಗುತ್ತಿಲ್ಲ, ತೊಂದರೆ)  → breath + difficulty
- ಮಾತ್ರೆ + (ಜಾಸ್ತಿ, ತುಂಬಾ, ಎಲ್ಲಾ) + (ತಗೊಂಡ, ತೆಗೆದುಕೊಂಡ, ನುಂಗ)  → took too many tablets

### 2c. Rules

- Normalise as in section 0 before matching.
- Keep every list as a constant at the top of safety.py so new real-world phrasings can be added without code changes.
- Log every emergency transcript (QuestionLog outcome `emergency`) so the caregiver sees it.

### 2d. Human follow-up (not for Freebuff)

The human will record 8 to 10 real spoken emergency phrasings, run them through Prisma, and add the exact transcripts to 2a. Real Prisma output beats guessed spellings.

## 3. Intent keywords (intent.py)

Spoken forms first, formal forms as backup. Check in this priority order; the first intent with any match wins:

1. DAYS_LEFT — ಎಷ್ಟ್ ದಿನ, ಎಷ್ಟು ದಿನ, ಇನ್ನೆಷ್ಟು ದಿನ, ಇನ್ನೂ ಎಷ್ಟ್, ಎಷ್ಟು ದಿವಸ, ದಿನ, ದಿವಸ, ಮುಗೀತು, ಮುಗಿಯುತ್ತೆ, ಮುಗಿ, ಎಲ್ಲಿವರೆಗೂ | eshtu dina, esht dina, innestu dina, dina, divasa, mugi | how many days, days, how long, finish
2. FOOD — ಊಟ, ತಿಂಡಿ, ತಿಂದ್ಮೇಲೆ, ತಿಂದ, ತಿನ್ನೋಕೆ, ಖಾಲಿ ಹೊಟ್ಟೆ, ಹೊಟ್ಟೇಲಿ | oota, uta, tindi, tindmele, khaali hotte | food, eat, meal, empty stomach, before food, after food
3. WHEN — ಯಾವಾಗ, ಯಾವಾಗ್, ಎಷ್ಟೊತ್ತಿಗೆ, ಎಷ್ಟ್ ಹೊತ್ತಿಗೆ, ಯಾವ್ ಟೈಮ್, ಯಾವ ಟೈಮ್, ಯಾವ ಹೊತ್ತು, ಟೈಮ್ | yaavaga, yavaga, eshtottige, yaav time, time | when, what time
4. HOW_MANY — ಎಷ್ಟ್, ಎಷ್ಟು, ಎಷ್ಟೊಂದು, ಎಷ್ಟ್ ಮಾತ್ರೆ | eshtu, estu, esht | how many, how much, dose
5. PURPOSE — ಯಾಕೆ, ಯಾಕ್, ಯಾತಕ್ಕೆ, ಏತಕ್ಕೆ, ಏನಕ್ಕೆ, ಯಾವ್ದಕ್ಕೆ, ಯಾವುದಕ್ಕೆ, ಏನ್ ಮಾತ್ರೆ, ಏನು ಮಾತ್ರೆ | yaake, yake, yaatakke, yenakke, yaavdakke, yen maatre | why, what for, what is it for

No match → UNKNOWN (→ referral).
Notes: "ಎಷ್ಟ್ ದಿನ" must resolve to DAYS_LEFT and "ಎಷ್ಟೊತ್ತಿಗೆ" to WHEN, not HOW_MANY; the priority order handles both.

## 4. Medicine matching vocabulary (matching.py and caregiver form)

Matching compares the normalised transcript against each confirmed medicine's `name`, `aliases`, `label`, `color_word`.
Because transcripts arrive in Kannada script, the caregiver form must tell the caregiver:
- **Label in Kannada script**, e.g. ಬಿಳಿ ಗುಂಡು ಮಾತ್ರೆ (white round tablet).
- **Colour word in Kannada script**, chosen from a dropdown:
  ಬಿಳಿ (white), ಹಳದಿ (yellow), ಕೆಂಪು (red), ನೀಲಿ (blue), ಹಸಿರು (green), ಕಿತ್ತಳೆ (orange), ಗುಲಾಬಿ (pink), ಕಪ್ಪು (black), ಕಂದು (brown)
- **Aliases** may mix scripts: e.g. BP tablet, ಬಿಪಿ ಮಾತ್ರೆ, ಬಿಪಿ ಟ್ಯಾಬ್ಲೆಟ್, ಶುಗರ್ ಮಾತ್ರೆ.
- **Dose** written in Kannada or as a number + ಮಾತ್ರೆ, e.g. `1 ಮಾತ್ರೆ` or `ಅರ್ಧ ಮಾತ್ರೆ`.
- Add a Roman `color_word_roman` field? **No** — keep one colour word in Kannada script; put the Roman form (bili, haladi, kempu…) into aliases automatically from this map:
  ಬಿಳಿ→bili, ಹಳದಿ→haladi, ಕೆಂಪು→kempu, ನೀಲಿ→neeli, ಹಸಿರು→hasiru, ಕಿತ್ತಳೆ→kittale, ಗುಲಾಬಿ→gulabi, ಕಪ್ಪು→kappu, ಕಂದು→kandu

Seed data (T2) should be updated to use Kannada-script labels and colour words.

## 6. Robustness additions (approved)

### 6a. Fuzzy keyword matching (intent.py and safety.py)
- First try exact substring match (sections 2 and 3). If nothing matched, try fuzzy: for each keyword of **4+ characters**, `rapidfuzz.fuzz.partial_ratio(keyword, transcript)`.
- Thresholds as constants: emergency `EMERGENCY_FUZZY = 85`, intent `INTENT_FUZZY = 88`. Keywords under 4 characters are exact-match only (avoids false matches).
- Emergency pair rules (2b) stay substring-based on stems.

### 6b. Ask back once instead of giving up (pipeline.py + answers.py)
New template key (add to kn.json):
`"clarify_question": "{label} ಬಗ್ಗೆ ಏನು ಬೇಕು? ಯಾವಾಗ ತಗೋಬೇಕು, ಎಷ್ಟು ತಗೋಬೇಕು, ಅಥವಾ ಊಟಕ್ಕೆ ಮುಂಚೆನಾ ಆದ್ಮೇಲಾ?"`
New outcome value: `clarify_question`.

Rules, using the profile's most recent QuestionLog row (same profile, within `FOLLOWUP_SECONDS = 120`):
1. Medicine matched, intent UNKNOWN → if the previous row is **not** `clarify_question` → outcome `clarify_question` (log the medicine_id). If it **is** → outcome `referral` (ask back only once).
2. Intent known, no medicine matched → if the previous row was `clarify_question` with a medicine_id → use that medicine (follow-up like just "ಯಾವಾಗ?").
3. Medicine matched, intent UNKNOWN, previous row was `clarify_which` with a known intent → use that intent (follow-up like just "ಬಿಳಿ").
4. Everything else as in FREEBUFF_TASKS_v4.md section 7.
Emergency check still runs first on every request.

### 6c. Prisma keyterms (pipeline.py → stt.transcribe)
- Docs (verified): `keyterms` works only on `prisma-v3.0`; JSON array or comma-separated; up to **200** entries; exceeding returns `400 INVALID_CONTEXT`. (`bias_list` + `bias_score` is the separate Prisma v2.5 mechanism; not used.)
- Send `keyterms` as a JSON-array string form field, built from the profile's **confirmed** medicines: name, aliases, label, colour word (Kannada + Roman), plus the fixed words ಮಾತ್ರೆ, ಊಟ, ಯಾವಾಗ, ಎಷ್ಟು. Deduplicate, cap at 100.
- Only send when `GNANI_STT_MODEL` is `prisma-v3.0`; controlled by env `GNANI_STT_KEYTERMS` (default `true`).
- If Prisma returns `400 INVALID_CONTEXT`, retry once without keyterms and log a warning.

## 5. Tests T4 must include (in addition to those in FREEBUFF_TASKS_v4.md)

- `ಈ ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ ತಗೋಬೇಕು?` with a confirmed white tablet (morning + night) → outcome answered, text = "<label>. ಇದನ್ನ ಬೆಳಿಗ್ಗೆ ಮತ್ತೆ ರಾತ್ರಿ ತಗೊಳ್ಳಿ."
- `ಎದೆ ನೋವು ಆಗ್ತಿದೆ, ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ?` → emergency (beats everything)
- `ಎದೆ ತುಂಬಾ ಭಾರ ಆಗ್ತಿದೆ` → emergency (pair rule)
- `ಉಸಿರಾಡೋಕೆ ತುಂಬಾ ಕಷ್ಟ ಆಗ್ತಿದೆ` → emergency (pair rule)
- `ಅಮ್ಮ ಜಾಸ್ತಿ ಮಾತ್ರೆ ತಗೊಂಡ್ಬಿಟ್ರು` → emergency
- `ಬಿಪಿ ಮಾತ್ರೆ ಯಾವಾಗ?` → NOT emergency
- `ಬಿಳಿ ಮಾತ್ರೆ ಎಷ್ಟೊತ್ತಿಗೆ ತಗೋಬೇಕು?` → WHEN (not HOW_MANY)
- `ತಿಂದ್ಮೇಲೆ ತಗೋಬೇಕಾ?` with one confirmed medicine → FOOD
- `ಇನ್ನೂ ಎಷ್ಟು ದಿನ ತಗೋಬೇಕು?` with one confirmed medicine that has days_total + start_date → days_left
- `ಇದನ್ನ ಹಾಲಿನ ಜೊತೆ ತಗೋಬಹುದಾ?` (can I take it with milk?) with one confirmed medicine → first time `clarify_question`; asked again within 120 s → `referral`
- `ಬಿಳಿ ಮಾತ್ರೆ ಬಗ್ಗೆ` → `clarify_question`; then just `ಯಾವಾಗ?` within 120 s → answered (when) for the white tablet
- fuzzy: `ಯಾವಗ ತಗೋಬೇಕು ಬಿಳಿ ಮಾತ್ರೆ` (misheard ಯಾವಾಗ) → WHEN
- keyterms: the request to Prisma includes a `keyterms` field built from confirmed medicines only (unconfirmed medicine names must not appear)
- Two confirmed white tablets → `ಬಿಳಿ ಮಾತ್ರೆ ಯಾವಾಗ?` → clarify_which listing both labels
