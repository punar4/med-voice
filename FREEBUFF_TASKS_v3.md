# FREEBUFF_TASKS.md (v3) — Build instructions for the coding agent

Read this whole file before writing any code. Work through the tasks **in order, one at a time**. After each task, stop and report: files changed, how to run it, and how to check it works.

---

## 1. What we are building

A voice assistant that lets an elderly person ask about **their own medicines** in Kannada and hear the answer spoken back.

- **Caregiver** (son/daughter, tech-comfortable): enters the prescription once, confirms every field, adds pill labels, sees a log of what the elder asked.
- **Elder** (low literacy, weak eyesight): opens a link on their phone, presses **one big button**, asks a question aloud, hears the answer.

This is a health app. **Every answer must come only from caregiver-confirmed prescription data.** The app never writes its own medical advice.

Built for the Gnani.ai Great Indian AI Internship Challenge. Must use Gnani **Prisma** (speech to text) and **Timbre** (text to speech).

---

## 2. Rules for the agent (follow strictly)

1. **One task at a time.** Do not start the next task until the current one works.
2. **Do not add features** that are not in this file.
3. **No secrets in code.** Read all keys from `.env` via `config.py`. Never print keys. `.env` must be in `.gitignore`.
4. **Do not guess Gnani API formats.** If the endpoint, auth header, request or response shape is unknown, stop and ask the human to paste the relevant part of docs.gnani.ai. Leave a clear `# TODO(gnani-docs)` comment.
5. **Protected files** — do not change their logic or rules without explicit human approval:
   - `backend/app/core/safety.py`
   - `backend/app/core/matching.py`
   - `backend/app/core/answers.py`
   - `backend/app/templates/*.json`
6. **Never write Kannada (or any) answer text yourself.** Use template keys only. The human provides the template text.
7. Keep dependencies minimal. Ask before adding anything not listed in section 3.
8. Synthetic data only. No real names, phone numbers or prescriptions in seed data.

---

## 3. Tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | `sqlmodel`: SQLite locally, hosted Postgres (Supabase free tier, database only: no Supabase auth or storage) when deployed. Switch only via `DATABASE_URL`; no code changes |
| Fuzzy matching | `rapidfuzz` |
| Audio conversion | `ffmpeg` (system binary), called via `subprocess` |
| Config | `python-dotenv` |
| Frontend | React + TypeScript (Vite), Tailwind CSS |
| Routing (frontend) | `react-router-dom` |
| Deploy | Render, one Docker web service: FastAPI serves the built frontend from `frontend/dist`, so there is one HTTPS origin (needed for mic access). Docker guarantees `ffmpeg` is installed |
| Postgres driver | `psycopg[binary]` (only needed in deployment) |

---

## 4. Folder structure

```
prescription-voice/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, routes, serves frontend build
│   │   ├── config.py          # loads .env
│   │   ├── db.py              # SQLite engine + session
│   │   ├── models.py          # Profile, Medicine, QuestionLog
│   │   ├── gnani/
│   │   │   ├── stt.py         # Prisma wrapper: transcribe(audio_bytes, lang) -> str
│   │   │   └── tts.py         # Timbre wrapper: synthesize(text, lang) -> bytes
│   │   ├── core/
│   │   │   ├── pipeline.py    # the /ask flow, wires everything together
│   │   │   ├── safety.py      # PROTECTED: emergency detection
│   │   │   ├── intent.py      # question type detection
│   │   │   ├── matching.py    # PROTECTED: medicine matching against confirmed list
│   │   │   └── answers.py     # PROTECTED: fills templates
│   │   ├── audio.py           # ffmpeg conversion helpers
│   │   └── templates/
│   │       └── kn.json        # PROTECTED: Kannada answer templates (human-written)
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── CaregiverSetup.tsx
│       │   ├── CaregiverLog.tsx
│       │   └── Elder.tsx
│       ├── lib/
│       │   ├── api.ts         # typed API client
│       │   └── recorder.ts    # MediaRecorder helper
│       └── App.tsx
├── scripts/
│   ├── batch_test.py          # runs a folder of audio clips through /ask, writes CSV
│   └── to_8khz.sh             # downsamples clips to 8 kHz (phone quality)
├── .github/workflows/keepalive.yml
├── Dockerfile
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. Data model (`models.py`)

**Profile**
- `id`, `elder_name` (display only), `language` (default `"kn"`), `share_token` (random, URL-safe), `created_at`

**Medicine**
- `id`, `profile_id`
- `name` (as on prescription, e.g. "Amlodipine 5mg")
- `aliases` (JSON list of other ways it may be said, e.g. ["BP tablet", "amlo"])
- `label` (how the elder knows it, e.g. "white round tablet" / "bili gundu maatre")
- `color_word` (e.g. "bili", "haladi", "kempu") — used for matching
- `photo_path` (optional)
- `dose` (e.g. "1 tablet")
- `times` (JSON list from: `"morning"`, `"afternoon"`, `"night"`)
- `food` (`"before"`, `"after"`, `"any"`)
- `days_total` (int, optional), `start_date` (date, optional)
- `purpose` (optional; only if written on the prescription)
- `confirmed` (bool, default `false`)

**QuestionLog**
- `id`, `profile_id`, `created_at`
- `transcript`, `intent`, `medicine_id` (nullable)
- `outcome` (`"answered"`, `"clarify"`, `"referral"`, `"emergency"`)
- `answer_key` (template key used), `answer_text`

**Rule:** the elder side only ever sees medicines where `confirmed = true`.

---

## 6. API routes

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/profiles` | Create profile, returns `id` and `share_token` |
| GET | `/api/profiles/{id}` | Profile + all medicines |
| POST | `/api/profiles/{id}/medicines` | Add medicine (unconfirmed) |
| PUT | `/api/medicines/{id}` | Edit medicine (sets `confirmed = false` again) |
| POST | `/api/medicines/{id}/confirm` | Caregiver confirms the medicine |
| DELETE | `/api/medicines/{id}` | Remove medicine |
| GET | `/api/profiles/{id}/log` | Question log, newest first |
| GET | `/api/health` | `{"ok": true}`, no database access |
| GET | `/api/health/db` | Runs `SELECT 1` on the database, returns `{"ok": true}`; used by the keep-alive workflow |
| GET | `/api/elder/{token}` | Minimal elder view: language + confirmed medicines' labels/photos only |
| POST | `/api/elder/{token}/ask` | Upload audio, run pipeline, return answer |

`/ask` response:
```json
{
  "transcript": "string",
  "outcome": "answered | clarify | referral | emergency",
  "answer_text": "string",
  "audio_base64": "string (wav/mp3 from Timbre)",
  "medicine": { "label": "string", "photo_url": "string | null" } 
}
```

---

## 7. The `/ask` pipeline (`pipeline.py`) — exact order

1. Convert uploaded audio to the format Prisma needs (ffmpeg; confirm format from docs).
2. `stt.transcribe()` → transcript.
3. `safety.check(transcript)` → if emergency: outcome `emergency`, template key `emergency_108`. **Skip all other steps except TTS and logging.**
4. `intent.detect(transcript)` → one of `WHEN`, `HOW_MANY`, `FOOD`, `PURPOSE`, `DAYS_LEFT`, `UNKNOWN`.
5. `matching.match(transcript, confirmed_medicines)` → one medicine, or ambiguous, or none.
6. `answers.build(intent, match_result, medicine, language)`:
   - clear match + known intent → outcome `answered`
   - ambiguous match → outcome `clarify` (asks which tablet, listing labels)
   - `UNKNOWN` intent, or the field is empty (e.g. no `purpose` written) → outcome `referral` ("please ask your doctor or pharmacist")
   - no medicine match but known intent → outcome `clarify`
7. `tts.synthesize(answer_text, language)`.
8. Save a `QuestionLog` row.
9. Return the response.

If STT or TTS fails, return a fixed fallback key `error_try_again` and still log it.

---

## 8. Safety rules (implement exactly; changes need approval)

**safety.py**
- Keyword list stored as a constant at the top of the file, in three forms: English, Kannada script, Kanglish (romanised).
- Normalise transcript: lowercase, strip punctuation, collapse spaces.
- Any keyword present → emergency.
- Starter list (human will verify and extend): `chest pain`, `can't breathe`, `cannot breathe`, `breathing problem`, `unconscious`, `fainted`, `ede novu`, `ಎದೆ ನೋವು`, `usiru kashta`, `ಉಸಿರಾಟ ಕಷ್ಟ`.
- Runs **before** any other logic.

**matching.py**
- Candidates: only the profile's **confirmed** medicines.
- Compare normalised transcript against each medicine's `name`, `aliases`, `label`, `color_word` using `rapidfuzz.fuzz.partial_ratio`.
- Best score ≥ 80 and at least 10 points above the second best → single match.
- Two or more candidates ≥ 80 within 10 points → ambiguous.
- Profile has exactly one confirmed medicine and nothing else matched → use it.
- Otherwise → no match.
- Thresholds are constants at the top of the file.

**answers.py**
- Only fills placeholders in templates with confirmed medicine fields.
- No arithmetic on doses. `DAYS_LEFT` = `days_total` minus days since `start_date`; if either is missing → `referral`.
- Unknown template key → raise an error (never fall back to generated text).

---

## 9. Templates (`templates/kn.json`)

Create the file with these **keys** and English placeholder values marked `TODO_KN`. The human will replace them with Kannada.

```json
{
  "when": "TODO_KN: {label} — take at {times}",
  "how_many": "TODO_KN: {label} — {dose}",
  "food": "TODO_KN: {label} — {food} food",
  "purpose": "TODO_KN: {label} — {purpose}",
  "days_left": "TODO_KN: {label} — {days} days left",
  "clarify_which": "TODO_KN: which tablet? {options}",
  "clarify_repeat": "TODO_KN: please say the tablet colour or name again",
  "referral": "TODO_KN: please ask your doctor or pharmacist",
  "emergency_108": "TODO_KN: call 108 now",
  "error_try_again": "TODO_KN: please press the button and ask again",
  "time_morning": "TODO_KN: morning",
  "time_afternoon": "TODO_KN: afternoon",
  "time_night": "TODO_KN: night",
  "food_before": "TODO_KN: before",
  "food_after": "TODO_KN: after",
  "food_any": "TODO_KN: with or without"
}
```

---

## 10. Tasks (in order)

### T0 — Project setup  _(Sat 7 Nov)_
- Create the folder structure, `requirements.txt`, Vite React TS app with Tailwind, `.gitignore` (include `.env`, `*.db`, `node_modules`, `dist`, `__pycache__`), `.env.example` with `GNANI_API_KEY=`, `GNANI_BASE_URL=`, `MOCK_GNANI=true`, `DATABASE_URL=sqlite:///./app.db`.
- **Done when:** `uvicorn app.main:app --reload` serves `GET /api/health` → `{"ok": true}` and `npm run dev` shows a blank app.

### T1 — Gnani wrappers with mock mode  _(Sat 7 Nov)_
- `stt.transcribe(audio_bytes, lang) -> str` and `tts.synthesize(text, lang) -> bytes`.
- If `MOCK_GNANI=true`: STT returns a fixed test transcript (configurable), TTS returns a short silent WAV. This lets everything else be built without spending credits.
- Real mode: implement only after the human pastes the Prisma and Timbre docs. Follow rule 4.
- **Done when:** a small test calls both in mock mode successfully.

### T2 — Database and models  _(Sat 7 Nov)_
- `models.py` and `db.py` per section 5; create tables on startup.
- Seed script with **one synthetic profile** and 3 synthetic medicines (2 confirmed, 1 unconfirmed).
- **Done when:** seed runs and `GET /api/profiles/{id}` returns them.

### T3 — Caregiver setup (API + UI)  _(Sat 7 Nov night, or Sun 8 Nov morning)_
- Routes from section 6 for profiles and medicines.
- `CaregiverSetup.tsx`: create profile; add medicine form (all fields in section 5); list of medicines with a clear **Confirm** button each; unconfirmed items visibly marked; editing a field un-confirms it; shows the elder link (`/elder/{share_token}`) with a copy button.
- **Done when:** a caregiver can add, edit, confirm and delete medicines in the browser.

### T4 — Core logic skeleton + pipeline  _(Sun 8 Nov)_
- Implement `safety.py`, `intent.py`, `matching.py`, `answers.py`, `pipeline.py` exactly per sections 7–9.
- `intent.py`: keyword rules for now (Kannada script + Kanglish + English), e.g. WHEN: "yaavaga", "yavaga", "when", "time", "ಯಾವಾಗ"; HOW_MANY: "eshtu", "how many", "ಎಷ್ಟು"; FOOD: "oota", "food", "ಊಟ"; PURPOSE: "yaake", "why", "what for", "ಯಾಕೆ"; DAYS_LEFT: "dina", "days", "ದಿನ". Keep lists as constants; the human will extend them. Structure it so an LLM-based detector can be swapped in later behind the same function signature.
- Unit tests in `backend/tests/` covering: emergency wins over everything; ambiguous match → clarify; unconfirmed medicine never matched; missing field → referral.
- **Done when:** tests pass and `POST /api/elder/{token}/ask` works in mock mode.

### T5 — Elder page  _(Sun 8 Nov)_
- `Elder.tsx` at `/elder/:token`. Mobile-first.
- One very large round mic button (at least 60% of screen width). Press to start recording, press again to stop (also auto-stop after 10 seconds).
- While processing: simple, large "listening/thinking" state.
- Show the answer as **large text** (min 24px), the matched pill's label/photo if any, and play the audio automatically.
- A large "say it again" button that replays the last audio.
- Emergency outcome: full-screen red banner with "108" in very large text plus the spoken message.
- No menus, no login, no settings, no other buttons.
- `recorder.ts`: MediaRecorder helper; send audio as multipart form data.
- **Done when:** on a phone (via the deployed HTTPS URL or localhost on desktop), pressing the button and speaking returns and plays an answer in mock mode.

### T6 — Caregiver question log  _(Sun 8 Nov)_
- `CaregiverLog.tsx`: table of questions (time, transcript, outcome, answer). Outcome colour tags: answered (neutral), clarify (amber), referral (highlighted), emergency (red, pinned at top).
- Simple counts at the top: questions today, referrals today, emergencies.
- **Done when:** questions asked on the elder page appear in the log after refresh.

### T7 — Test scripts  _(Mon 9 Nov)_
- `scripts/to_8khz.sh`: converts every file in an input folder to 8 kHz mono WAV in an output folder (ffmpeg).
- `scripts/batch_test.py`: reads a CSV (`file, expected_intent, expected_medicine, expected_outcome`), posts each clip to `/ask`, writes a results CSV with a pass/fail column and prints accuracy.
- **Done when:** running on 3 sample clips produces a results CSV.

### T8 — Polish and deploy  _(Mon 9 Nov)_
- Build the frontend; FastAPI serves `frontend/dist` and falls back to `index.html` for client routes.
- Mobile layout check on a narrow screen; large tap targets; high contrast.
- README: setup, env vars, run, deploy, how to run tests and batch tests.
- `Dockerfile` (multi-stage): stage 1 builds the frontend with Node; stage 2 is a Python image that installs `ffmpeg` via apt, installs `requirements.txt`, copies the backend and `frontend/dist`, and runs Uvicorn on `$PORT`.
- Database: code must work unchanged with both `sqlite:///...` and `postgresql+psycopg://...` URLs. Do not use SQLite-only features. Tables are created on startup in both cases.
- Add `psycopg[binary]` to `requirements.txt`.
- README section "Deploy to Render": create a free Supabase project, copy its Postgres connection string and change the prefix to `postgresql+psycopg://`, create a Render web service from the repo using the Dockerfile, set env vars (`DATABASE_URL`, `GNANI_API_KEY`, `GNANI_BASE_URL`, `MOCK_GNANI=false`). Note that the free tier sleeps when idle, so open the URL a minute before any demo.
- Add `GET /api/health/db` (see section 6).
- **Done when:** the deployed HTTPS URL works on a phone end to end, and data survives a redeploy.

### T9 — Keep-alive workflow  _(Tue 10 Nov, after submission)_
- `.github/workflows/keepalive.yml`: runs every 2 days (`cron: "0 6 */2 * *"`) and on `workflow_dispatch`.
- One step: `curl -fsS --retry 3 --retry-delay 30 --max-time 90 "${{ secrets.APP_URL }}/api/health/db"`.
- README: add `APP_URL` as a repository secret; run the workflow manually once to test.
- **Done when:** a manual run succeeds and shows the 200 response.

---

## 11. Out of scope (do not build)

Spoken reminders, phone-call access, multiple caregivers, login/auth beyond the share token, refill alerts, handwriting OCR, any language other than Kannada (structure must allow adding `hi.json` later without code changes).
