# Solwin — Full-Stack Run Guide

Four services run together: ML service (:8000), Backend API (:8001), Data API (:8002, raw
feedback inbox), Frontend (:5173). Default databases are SQLite so no Postgres is needed
for local runs.

## 1. Reproduce the artifacts (fresh checkout)

1. **Python deps**
   - ML service: `cd app/ml_services` — use its committed `.venv` (or `pip install -e .`).
   - Backend: `cd app/Backend && uv sync` (or `python -m pip install -r requirements.txt`).

2. **Frontend deps**: `cd app/frontend && npm install`.

3. **Backend env file**: copy `app/Backend/.env` from the main checkout into the same
   path of your worktree (it is gitignored). It sets `DATABASE_URL` to
   `sqlite:///./solwin_dev.db`, `ML_SERVICE_URL=http://localhost:8000`, and reads
   `GEMINI_API_KEY` / `GEMINI_MODEL` — supply your own Gemini key value; never commit it.

4. **Frontend env file**: copy `app/frontend/.env` from the main checkout. It contains
   `VITE_API_BASE_URL=http://localhost:8001/api/v1` and (for the Inbox page)
   `VITE_DATA_API_BASE_URL=http://localhost:8002`.

5. **Data API database** (raw feedback inbox, ~20.9k records):
   ```
   cd app/data && DATABASE_URL=sqlite:///inbox_dev.db \
     uv run --project ../Backend python -m backend.seed
   ```
   Reads `app/data/unified_customer_phishing_data.csv`, cleans/dedupes it
   (28,942 → 20,862 records), and writes `app/data/inbox_dev.db` (gitignored).

6. **Database + demo data** (safe to re-run; skips if already seeded):
   ```
   cd app/Backend && uv run python scripts/bootstrap_local.py
   ```
   Creates tables, a demo agent, and 6 conversations with real Gemini analysis
   (requires the key) plus deterministic local threat scoring.

## 2. Run the servers

Start in this order (Backend calls ML; Frontend calls Backend):

```
# 1. ML service on :8000
# NOTE: without app/ml_services/.env containing GEMINI_ENABLED=true + GEMINI_API_KEY,
# sentiment falls back to NEUTRAL (LLM off) — copy the two GEMINI_* lines from
# app/Backend/.env to give it real AI sentiment.
cd app/ml_services && .venv/bin/uvicorn ml_service.main:app --host 127.0.0.1 --port 8000

# 2. Backend API on :8001
cd app/Backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8001

# 3. Data API (raw feedback inbox) on :8002
cd app/data && DATABASE_URL=sqlite:////absolute/path/to/app/data/inbox_dev.db \
  ../Backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8002

# 4. Frontend on :5173
cd app/frontend && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Health checks: `GET /health` on :8000 and :8001; Frontend root returns the SPA.

### Detached on macOS (launchd)

The command runner may reap plain background processes. If so:

```
launchctl submit -l solwin-preview-vite -- /bin/sh -c \
  "cd <repo>/app/frontend && PATH=/usr/local/bin:/usr/bin:/bin exec npm run dev -- --host 127.0.0.1 --port 5173 --strictPort > <log> 2>&1"
```

Notes learned the hard way:
- launchd does **not** inherit the interactive shell PATH — `npm` needs the explicit
  `PATH=/usr/local/bin:/usr/bin:/bin` prefix (node is installed in `/usr/local/bin`).
- Read the pid via `launchctl print gui/$(id -u)/solwin-preview-vite | grep pid`.
- Remove with `launchctl remove solwin-preview-vite` when done.

## 3. Stop / reset

- Reset demo data: stop servers, delete `app/Backend/solwin_dev.db`, re-run bootstrap.
- Backend test suite: `cd app/Backend && uv run pytest` (no DB or network needed).
- ML test suite: `cd app/ml_services && .venv/bin/python -m pytest`.

## Containerized stack (Docker / Cloud Run)

Production containers live in each service dir (`app/*/Dockerfile`) plus the
integrated `docker-compose.yml` at the repo root (4 services + Postgres).
Google Cloud path: `gcloud builds submit --config deploy/cloudbuild.yaml .`
then follow `deploy/README-gcp.md` (Cloud Run + Cloud SQL + Secret Manager).

## Data API notes (:8002)

- The attachments router creates its upload dir at import time; set `UPLOAD_DIR` to a
  writable path if the default (`app/data/backend/uploads`) is not writable.
- `GET /tickets` supports `skip`, `limit` (≤500), `intent`, `search` (subject/message/issue,
  case-insensitive), `phishing` (true/false), `priority` (CRITICAL/HIGH/MEDIUM/LOW).
  Listing order is a **FIFO priority queue**: priority tier first, oldest-first within a
  tier (`priority_rank ASC, created_at ASC, id ASC`). Priority is derived deterministically
  from dataset signals in `backend/priority.py` (phishing flag > technique > intent >
  issue > label; first match wins, default LOW).
- `GET /tickets/facets` returns `{total, phishing, intents[], priority_counts}` for the
  Inbox tab/filter badges. A 20-row page answers in ~3ms.
- `GET /tickets/stats` returns `{total_records, phishing_flagged, priority_counts,
  top_intents}`; the Backend's `/api/v1/dashboard/overview` merges this into its response
  as `ingested_feedback` (null when the Data API is down — dashboard degrades gracefully).
