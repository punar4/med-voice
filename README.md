# MedVoice — medicine answers by voice, in Kannada

An elderly person presses one big button on their phone, asks about **their own**
medicines in Kannada, and hears the answer read back. A caregiver sets the
prescription up once and confirms every field; the app only ever answers from
that confirmed data — it never invents medical advice.

Built for the Gnani.ai Great Indian AI Internship Challenge, using Gnani
**Prisma** for speech-to-text and **Timbre** for text-to-speech.

---

## What is in the box

| Part | What it does |
| --- | --- |
| `backend/app/main.py` | FastAPI routes (profiles, medicines, elder view, `/ask`, health) and serving of the built frontend |
| `backend/app/core/` | The answer flow: safety → intent → medicine matching → template answers |
| `backend/app/gnani/` | Prisma and Timbre wrappers, with a mock mode for working without credits |
| `frontend/src/pages/` | Caregiver setup, caregiver question log, elder voice page |
| `scripts/batch_test.py` | Runs a folder of recorded clips through `/ask` and scores them against `test_audio/expected.csv` |
| `scripts/to_8khz.sh` | Downsamples a folder of clips to 8 kHz mono WAV (phone quality) |
| `Dockerfile` | Multi-stage build: Node builds the frontend, Python + ffmpeg serves API and UI |

---

## Run it locally

Requirements: **Python 3.11+**, **Node 20+**, and **ffmpeg** on your PATH
(Windows: `winget install ffmpeg`; macOS: `brew install ffmpeg`; Debian/Ubuntu:
`sudo apt install ffmpeg`).

```bash
# 1. environment (never commit .env)
cp .env.example .env          # then fill in the values below

# 2. backend
python -m venv venv
venv/Scripts/python.exe -m pip install -r backend/requirements.txt   # Windows
# source venv/bin/activate && pip install -r backend/requirements.txt  # macOS/Linux

cd backend
python seed.py                # prints the profile id, share token and elder link
uvicorn app.main:app --reload # http://127.0.0.1:8000
```

```bash
# 3. frontend, in a second terminal
cd frontend
npm install
npm run dev                   # http://localhost:5173, /api proxied to :8000
```

Open `http://localhost:5173`, add and **confirm** a medicine, then open the
elder link it shows. Press the big button, ask, listen.

### Serve the built frontend like production

```bash
cd frontend && npm run build      # writes frontend/dist
cd ../backend && uvicorn app.main:app
```

Now `http://127.0.0.1:8000` serves the app itself, and refreshing
`/elder/<token>` still works (unknown non-API paths return `index.html`).

---

## Environment variables

Copy `.env.example` to `.env`. Nothing secret belongs in a tracked file.

| Name | Required | What it is |
| --- | --- | --- |
| `GNANI_API_KEY` | yes, when `MOCK_GNANI=false` | Gnani API key. Read only from the environment, never printed or logged |
| `GNANI_BASE_URL` | yes, when `MOCK_GNANI=false` | Gnani API base URL (e.g. `https://api.gnani.ai`) |
| `MOCK_GNANI` | no (default `true`) | `true` returns a fixed transcript and silent audio, so the app runs without spending credits. **Must be `false` when deployed** |
| `DATABASE_URL` | no (default `sqlite:///./app.db`) | `sqlite:///./app.db` locally, `postgresql+psycopg://...` in production |
| `GNANI_STT_MODEL`, `GNANI_STT_FORMAT`, `GNANI_STT_KEYTERMS` | no | Prisma model (`prisma-v3.0`), input format (`codemix`), and whether to bias recognition with the medicine words |
| `GNANI_TTS_MODEL`, `GNANI_TTS_VOICE`, `GNANI_TTS_SPEED` | no | Timbre model (`timbre-v2.5`), voice (`Saanvi`), speaking speed (`0.9`) |
| `PORT` | set by the host | Uvicorn port in the container (Render sets it) |

The database code is identical for SQLite and Postgres — only `DATABASE_URL`
changes, and tables are created on startup in both cases.

---

## Tests

```bash
cd backend
python -m pytest            # core logic, routes, Gnani wrappers (mock mode)
```

```bash
cd frontend
npm run lint
npm run build
```

### Batch test of recorded clips

`scripts/batch_test.py` sends every clip listed in `test_audio/expected.csv`
through `/ask` and writes `test_audio/results.csv` with the transcript, outcome,
matched tablet label and pass/fail, then prints overall accuracy, emergency
recall and per-outcome counts.

```bash
# server running in another terminal, with MOCK_GNANI=false and the key in .env
python scripts/batch_test.py --profile-id <id printed by seed.py>
```

Each clip is asked on its own throwaway profile (cloned from the seeded
profile's confirmed medicines), so one question can never be treated as a
follow-up of the previous one. Useful flags: `--limit 3`, `--out path.csv`,
`--base-url`, `--timeout`. To try the plumbing without credits, add
`--allow-mock` with `MOCK_GNANI=true`.

Clips in other formats can be normalised first (needs ffmpeg):

```bash
bash scripts/to_8khz.sh test_audio test_audio_8khz
```

---

## Deploy to Render

One Docker web service serving API and UI from the same HTTPS origin (the
microphone requires a secure origin, so a single origin is the simple choice).
Database: a free Supabase Postgres project.

1. **Supabase** → New project (free tier). Choose a region near you and save the
   database password somewhere safe.
2. In the project, open **Connect** (or *Project Settings → Database*) and copy
   the **Session pooler** connection string. It looks like
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
3. Change the prefix to the Psycopg form the app expects:
   `postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
   If the password contains `@`, `:`, `/` or `#`, percent-encode it.
4. **Render** → New → **Web Service** → connect the GitHub repo.
   - Language/runtime: **Docker** (Render finds the `Dockerfile` at the repo root).
   - Instance type: free.
   - Health check path: `/api/health/db`.
5. Add environment variables in Render (Environment tab):
   - `DATABASE_URL` = the `postgresql+psycopg://...` string from step 3
   - `GNANI_API_KEY` = your Gnani key
   - `GNANI_BASE_URL` = your Gnani base URL
   - `MOCK_GNANI` = `false`
6. Deploy. First build takes a few minutes (Node build + Python install + ffmpeg).
7. Check `https://<service>.onrender.com/api/health` → `{"ok": true}` and
   `/api/health/db` → `{"ok": true}`. Tables are created on the first startup.
8. Seed the deployed database once, from your machine, pointing at the same
   Postgres URL:

   ```bash
   DATABASE_URL="postgresql+psycopg://..." python backend/seed.py
   ```

   Then add real medicines through the caregiver page and open the elder link on
   a phone.

**Free tier sleeps:** an idle service spins down after a few minutes, and the
next request takes ~30–60 seconds. Open the URL a minute before any demo, then
refresh. The keep-alive workflow below pings the service so it stays awake — see
[Keep-alive](#keep-alive).

**Data survives redeploys** because it lives in Supabase, not in the container —
the container's filesystem is thrown away on every deploy.

---

## Keep-alive

`.github/workflows/keepalive.yml` calls `GET <APP_URL>/api/health/db` every 10
minutes (and on demand), retries once after 30 seconds, and fails the run if the
endpoint does not answer 2xx. That keeps the free Render instance from falling
asleep and doubles as an uptime check on the database.

The workflow never contains the URL. It reads the repository variable
`APP_URL`, so each fork or deployment points at its own service:

1. GitHub repo → **Settings** → **Secrets and variables** → **Actions**.
2. Open the **Variables** tab → **New repository variable**.
3. Name `APP_URL`, value your service URL with no trailing slash, e.g.
   `https://my-app.onrender.com`.
4. **Actions** → **Keep-alive** → **Run workflow** to test it manually. The run
   log should print `OK: HTTP 200` and `{"ok":true}`.

If `APP_URL` is not set, the job skips with a notice instead of failing, so a
fresh clone is never red. Nothing secret is involved — the URL is public — which
is why it is a variable and not a secret. GitHub's scheduled runs can be delayed
by a few minutes at busy times, which is fine for a keep-alive.

---

## Results

<!-- TODO(human): fill in after the final batch run. Keep it short and honest. -->

- Clips tested: `<n>` (normal speech `<n>`, emergency `<n>`)
- Overall outcome accuracy: `<x>%`
- Emergency detection (recall): `<x>%`
- Matched-tablet accuracy: `<x>%`
- Typical failure modes: `<...>`
- Median round trip on the deployed URL: `<n> s`

---

## How I built this

<!-- TODO(human): write this in your own voice. Suggested prompts below. -->

- The problem I wanted to solve: `<...>`
- What I built first, and what I learned from it: `<...>`
- The hardest bug and how I found it: `<...>`
- What I would build next: `<...>`

---

## Notes and limits

- Answers come only from caregiver-confirmed fields; when a field was never
  written down, the app says to ask a doctor or pharmacist instead of guessing.
- Emergencies are matched by keywords **before** anything else runs, and the
  answer tells the elder to call 108. It is a safety net, not a diagnosis.
- One language for now (Kannada). Templates are keyed by intent, so adding
  another language file needs no logic change.
- Recordings are processed for the answer and not stored; only the transcript,
  outcome and answer are kept in the question log.
