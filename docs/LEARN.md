# Learning log

## T0 — Project setup

**What we built:** The empty skeleton of the whole app — a FastAPI backend that answers a health check, and a Vite/React/TypeScript frontend with Tailwind that starts blank. Settings come from `.env` through `config.py`, and files that must never be committed are ignored.

**Files:**
- `backend/app/main.py` — the FastAPI app; for now it only has `GET /api/health`.
- `backend/app/config.py` — loads `.env` from the repo root and exposes the four settings; keeps keys out of the code.
- `backend/requirements.txt` — the backend packages the task list allows.
- `backend/app/{db,models,audio}.py` and `backend/app/core/*.py`, `backend/app/gnani/*.py` — named placeholder files so the final structure exists; the real logic arrives in T1–T4.
- `backend/app/templates/kn.json` — the answer template keys, still marked `TODO_KN` until the human writes the Kannada.
- `frontend/vite.config.ts`, `frontend/src/App.tsx`, `frontend/src/index.css` — Vite + React + Tailwind wired together, demo page removed.
- `.gitignore` and `.env.example` — repo hygiene: `.env`, `*.db`, `node_modules`, `dist` and `__pycache__` stay out of git, and the four setting names are documented with no values.

**How it fits:** Nothing user-facing happens yet. This is the shell that every later request will travel through: elder speaks → audio → Prisma → safety → intent → matching → answers → Timbre → log.

**Key concepts (one line each):**
- FastAPI route: a Python function that runs when a URL is called.
- Uvicorn: the server that runs the app; `--reload` restarts it on file changes.
- `python-dotenv`: reads a `.env` file into settings so secrets never sit in the code.
- Vite: dev server and bundler that turns TypeScript/React into files a browser can run.
- Tailwind: small utility CSS classes written in the markup instead of separate stylesheets.

**Later Learn:**
- FastAPI dependencies: how shared objects like DB sessions are injected into routes — needed in T2.
- Vite dev vs production build: why dev serves source files but deploy serves `frontend/dist` — needed in T8.
- Why secret files stay out of git history: what to do if a key is ever committed.

## T1 — Gnani wrappers with mock mode

**What we built:** Two functions that stand in for Gnani's cloud speech services: `transcribe()` turns recorded audio into text, `synthesize()` turns text into audio bytes. While `MOCK_GNANI=true` neither touches the network — speech to text returns one fixed test sentence and text to speech returns half a second of silence as a real WAV file — so the whole app can be built without credits or an API key. Real mode exists only as a clear error, because the Gnani request format is not known yet.

**Files:**
- `backend/app/gnani/stt.py` — `transcribe(audio_bytes, lang)`; mock returns the fixed transcript, real mode raises with a `TODO(gnani-docs)` note.
- `backend/app/gnani/tts.py` — `synthesize(text, lang)`; mock builds a silent 16 kHz mono WAV with the stdlib `wave` module, so no new dependency.
- `backend/app/gnani/__init__.py` — `GnaniNotConfigured`, one shared error so the pipeline can say "not ready" cleanly in T4.
- `backend/app/config.py` — adds `MOCK_STT_TRANSCRIPT`, the test question; change it in `.env` to try a different one.
- `backend/tests/test_gnani_mock.py` — four checks that both functions return usable results.
- `backend/tests/__init__.py` — empty, only so `unittest` can import the tests folder.

**How it fits:** The two ends of the flow: mic audio goes into Prisma (step 2) and answer audio comes out of Timbre (step 7). Everything between them is still stubs.

**Key concepts (one line each):**
- Mock mode: a fake but correctly-shaped implementation, so callers are written and tested before the real service is available.
- WAV file: a 44-byte header plus raw samples; ours is 16-bit mono, so every zero byte means silence.
- Config flag: one setting (`MOCK_GNANI`) switches the whole app between fake and real without code changes.
- Unit test: a small program that calls your code and fails loudly if the result is wrong.

**Later Learn:**
- Gnani Prisma and Timbre request formats — needed before real mode can replace the mocks.
- Audio streaming vs whole-file upload: why phones send a completed clip and how large that can get.
- Why mock data and real data must never mix in one database — protects the safety rules in T4.

## T2 — Database and models

**What we built:** The three real tables from section 5: `Profile` (one elder), `Medicine` (rows the caregiver enters) and `QuestionLog` (every question, filled in T4). `db.py` connects using `DATABASE_URL` and the app creates any missing tables on startup. A seed script adds one synthetic profile with three medicines — two confirmed, one left unconfirmed on purpose.

**Files:**
- `backend/app/models.py` — the three tables with every field from section 5; `aliases` and `times` are JSON columns so SQLite and Postgres behave the same; `share_token` gets a random value automatically.
- `backend/app/db.py` — the engine, `init_db()` to create tables, and `get_session()` as a FastAPI dependency (one session per request).
- `backend/app/main.py` — creates tables on startup and adds `GET /api/profiles/{id}`, which returns the profile plus all medicines or 404.
- `backend/seed.py` — inserts the synthetic profile and medicines; safe to re-run, it does nothing if the profile already exists.
- `backend/requirements.txt` — adds `pytest` (approved by the human).

**How it fits:** Steps 3–8 of the flow read and write these tables: matching only sees confirmed medicines, and every `/ask` writes one `QuestionLog` row.

**Key concepts (one line each):**
- ORM: a Python class per table, so you write objects instead of SQL strings.
- Foreign key: `Medicine.profile_id` points at a `Profile` row, so medicines belong to one elder.
- Dependency: `Depends(get_session)` hands the route a session and closes it afterwards, even on error.
- `create_all`: creates tables that are missing, but never changes a table that already exists.
- Idempotent script: running it twice leaves the same result, which makes it safe to re-run.

**Later Learn:**
- Migrations (Alembic): why `create_all` is enough today but loses data-safe column changes later.
- Postgres index types: how `share_token` lookups stay fast as profiles grow.
- Transactions: why a half-saved profile would be worse than no profile at all.

## T1 — Gnani real mode (Prisma + Timbre)

**What we built:** With `MOCK_GNANI=false` the two wrappers now make real HTTP calls: Prisma receives the clip as a file upload and returns text, Timbre receives JSON and returns WAV bytes. Responses are checked against the documented error shapes and turned into one `GnaniAPIError` carrying the status, error type and message. The API key is read once from settings, sent as a header, and never logged; mock mode is untouched.

**Files:**
- `backend/app/gnani/stt.py` — posts multipart to `/stt/v3` with `audio_file`, language code, model and format; an empty transcript is returned as `""`, not an error; `keyterms` is accepted but not sent yet, and the optional `filename` names and types the upload from the real clip name.
- `backend/app/gnani/tts.py` — posts JSON to `/api/v1/tts/inference` (text, model, voice, language, speed, audio config) and returns the WAV bytes, refusing any 200 that is not audio.
- `backend/tests/test_gnani_stt_upload.py` — checks the multipart part name and content type (real name, default `audio.wav`, and the `application/octet-stream` fallback).
- `backend/app/gnani/__init__.py` — `GnaniAPIError`, the error-body parser for all three shapes, the 30 s timeout, the `kn` → `kn-IN` map, and the missing-setting guard.
- `backend/app/config.py` + `.env.example` — five new settings (STT model/format, TTS model/voice/speed) with the documented defaults; `httpx` added to `requirements.txt` as approved.
- `scripts/try_gnani.py` — manual check: prints the Prisma transcript, speaks one fixed greeting through Timbre, saves `out.wav` (now git-ignored).

**How it fits:** These calls are steps 2 and 7 of the flow; everything between them (safety, intent, matching, answers) still runs on the mock-free data in the database.

**Key concepts (one line each):**
- Multipart upload: one text field per form value plus the file, unlike JSON.
- HTTP status vs `success`: a 200 body can still say `success: false`, so both must be checked.
- Fail loudly with context: one error type plus status and type means T4 can log a useful reason.
- Secrets hygiene: the key lives in one settings value and appears in no message or log line.
- Trust the file, not the label: Prisma picks the decoder from the uploaded file name, so an M4A sent as `audio.wav` failed with `AUDIO_CONVERSION_ERROR` ("invalid start code in RIFF header"); the caller now passes the real name and `mimetypes` types it.

**Later Learn:**
- `httpx` clients and connection reuse: why one shared client beats a call per request at scale.
- Audio codecs and sample rates: why Prisma wants ≤30 s clips and why we ask Timbre for 24 kHz.
- Retries with backoff for 429/5xx: when retrying is safe and when it double-charges.

## T3 — Caregiver setup (API + UI)

**What we built:** The caregiver's screen and the routes behind it: create a profile, add a medicine, edit it, confirm it, delete it. A medicine starts unconfirmed and an edit un-confirms it again, so the elder only ever hears about details the caregiver has checked. The page shows the elder link with a copy button, and unconfirmed rows are marked amber.

**Files:**
- `backend/app/main.py` — the six profile/medicine routes plus two input models; `confirmed` is never accepted from the browser, only set by the confirm route.
- `frontend/src/lib/api.ts` — typed client for those routes, with one place that turns an HTTP failure into a readable message.
- `frontend/src/pages/CaregiverSetup.tsx` — create profile, add/edit form with every section-5 field, medicine list with Confirm/Edit/Delete, elder link and copy button.
- `frontend/src/App.tsx` — shows the caregiver page; real routing arrives with the elder page in T5.
- `frontend/vite.config.ts` — dev-only proxy: `/api` calls from port 5173 go to the backend on 8000, so the same relative URLs work when deployed.
- `.gitignore` — un-ignores `frontend/src/lib/`, which the Python template's `lib/` rule was silently hiding from git.

**How it fits:** This fills the tables that step 5 (matching) may read: only rows with `confirmed = true` are ever candidates, so the caregiver's Confirm button is the gate on every spoken answer.

**Key concepts (one line each):**
- Input model (Pydantic): declares the fields and limits of a request body; wrong values get a 422 instead of reaching the database.
- PUT vs POST: POST creates a row, PUT replaces one that already exists.
- Un-confirm on edit: changing a dose invalidates an older "yes", so trust must be given again.
- Dev proxy: makes the frontend and backend look like one origin locally, so no CORS settings are needed.
- `localStorage`: remembers which profile this browser is editing; it is convenience, not security.

**Later Learn:**
- Share-token design: why a long random link is enough here and what login would add.
- Multipart file upload for pill photos, and where those files should live in deployment.
- Optimistic UI updates and lost-update conflicts when two tabs edit the same medicine.

## T4 — Core logic + /ask pipeline

**What we built:** The app's brain. A spoken question becomes text (Prisma), is checked for emergencies first, then sorted into a question type (when / how many / food / why / days left) and matched to one of the elder's *confirmed* tablets. The answer is a fixed Kannada sentence filled with the caregiver's confirmed details, spoken back by Timbre, and every question is logged for the caregiver. When unsure, it asks back once, then says "ask your doctor".

**Files:**
- `backend/app/core/safety.py` — emergency phrases (spoken Kannada, English-in-Kannada-script, Kanglish, English), word-pair rules (chest + pain, breath + difficulty, tablets + too many + took) and a fuzzy fallback. Always runs first.
- `backend/app/core/intent.py` — keyword lists per question type, checked in priority order, then a fuzzy pass; time-of-day words are a last-resort WHEN.
- `backend/app/core/matching.py` — fuzzy match against confirmed tablets only; ignores generic words like ಮಾತ್ರೆ; breaks ties between same-coloured tablets by their label; refuses to answer about a colour no confirmed tablet has.
- `backend/app/core/answers.py` — loads `templates/kn.json` and fills placeholders; joins times naturally; unknown keys raise instead of inventing text.
- `backend/app/core/pipeline.py` — `decide()` (pure rules, unit-tested) and `run()` (Prisma → decide → Timbre → QuestionLog).
- `backend/app/audio.py` — detects the real audio format from its first bytes; converts browser WebM to 16 kHz WAV with ffmpeg.
- `backend/app/gnani/stt.py` — sends the elder's medicine words as Prisma `keyterms`; retries without them on `INVALID_CONTEXT`.
- `backend/app/main.py` — `GET /api/elder/{token}`, `POST /api/elder/{token}/ask`, `GET /api/profiles/{id}/log`; saving a medicine adds the Roman colour alias.
- `frontend/src/pages/CaregiverSetup.tsx` — colour word is now a Kannada dropdown; Kannada placeholders.
- `backend/seed.py` — Kannada labels; two white tablets on purpose (to demo "which tablet?").
- `backend/tests/` — 60 tests incl. every case in T4_INPUTS_v4.

**How it fits:** This is the middle of the flow: elder speaks → audio → Prisma → **safety → intent → matching → answers** → Timbre → log. T5 (elder page) calls `/ask`; T6 (caregiver log) reads `/log`.

**Key concepts (one line each):**
- Rules before AI: deterministic keyword rules decide; nothing generates medical text.
- Fail safe: an unclear question gets one ask-back, then "ask your doctor"; a false emergency alarm is acceptable, a missed one is not.
- Pure function + thin wrapper: `decide()` has no I/O, so every rule is testable in milliseconds.
- Fuzzy matching (`rapidfuzz.partial_ratio`): scores 0–100 how well a short string appears inside a longer one.
- Magic numbers in files: the first bytes (RIFF, OggS, 1A45DFA3…) say what the audio really is, whatever its name.
- Follow-ups: the last log row within 120 s carries context ("ಯಾವಾಗ?" after "which tablet?").

**Outcomes `/ask` can return (for T5/T6):** `answered`, `clarify_which`, `clarify_question`, `clarify_repeat`, `referral`, `emergency`, `error`. The response also has `audio_error: true` if Timbre failed; the text answer is still shown.

**Later Learn:**
- How partial_ratio works on Kannada (code points vs letters) and why short words need exact matches.
- Why "ದಿನ" alone was a bad DAYS_LEFT keyword ("ದಿನಕ್ಕೆ ಎಷ್ಟು" = per day) — keyword design pitfalls.
- ffmpeg pipes (`pipe:0` / `pipe:1`) and why M4A can't always be read from a pipe.
- Evaluating safety rules: precision vs recall, and building a test set of real transcripts.
