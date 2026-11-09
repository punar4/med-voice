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
