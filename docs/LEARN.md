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
