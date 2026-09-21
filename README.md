# Solwin — AI-Powered Customer Support Intelligence & Security Platform

Solwin is an integrated enterprise customer intelligence and security platform. It analyzes inbound customer communications, classifies complaints into canonical business taxonomies, detects security threats (phishing, social engineering, malicious URLs, credential harvesting), evaluates urgency, and delivers actionable recommendations for customer support operations — at dataset scale (20,862 records) and per-conversation scale.

```
RAW FEEDBACK DATASET (28,942 records)
       │
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Data Service (app/data)        Ingestion + read-only serving plane │
│  clean → derive priority → seed → FastAPI :8002                     │
└─────────────────────────────────────────────────────────────────────┘
       │
       ├──────────────────────────────┐
       ▼                              ▼
┌──────────────────────────┐   ┌─────────────────────────────────────┐
│ ML Service (app/         │   │ Backend API (app/Backend)           │
│ ml_services) :8000       │   │ FastAPI :8001 · PostgreSQL          │
│ Tiered AI pipeline       │◄──┤ Unified analysis, persistence,      │
│ (local ML/NLP primary,   │   │ dashboard/analytics aggregation     │
│ Gemini summary-primary)  │   └─────────────────────────────────────┘
└──────────────────────────┘                │
       │                                    ▼
       │                   ┌─────────────────────────────────────┐
       └──────────────────►│ Frontend (app/frontend) :5173/8080  │
                           │ React operator console: Dashboard,  │
                           │ Inbox, Conversations, Threats,      │
                           │ Security & Customer Insights        │
                           └─────────────────────────────────────┘
```

## The four services

| Service | Path | Port | Role |
|---|---|---|---|
| **ML Service** | `app/ml_services` | 8000 | Tiered AI: local TF-IDF classifiers, NLP sentiment, rule-based social-engineering detection; Gemini for abstractive summaries + agreement cross-checks |
| **Backend API** | `app/Backend` | 8001 | Conversation & review APIs, AI analysis persistence, dashboard/analytics aggregation, threat intelligence |
| **Data Service** | `app/data` | 8002 | Canonical cleaning of the raw dataset, deterministic priority, read-only inbox serving (20,862 records) |
| **Frontend** | `app/frontend` | 5173 (dev) / 8080 (nginx) | Operator console — every page wired to live APIs, no mocks |

## Main pipelines

### 1. Ingestion pipeline (dataset → inbox)

Raw CSV → canonical cleaning (`app/data/backend/clean_data.py`: NFKC normalize, trim, null/duplicate handling) → deterministic priority assignment (`priority.py` rule cascade over phishing flag, technique, intent, issue, label) → bulk seed → **Data API** serving 20-per-page priority-first FIFO. Read-only at runtime; AI enrichment lives in the Backend DB keyed by `INBOX-<recordId>`.

### 2. AI inference pipeline (tiered)

Every analysis runs **local ML/NLP first** — TF-IDF + Logistic Regression classification into 11 canonical categories (with abstention via `needs_review`), lexicon NLP sentiment, and a 9-rule social-engineering detector — at zero API cost in milliseconds. One structured **Gemini** call then produces the abstractive summary and three agreement cross-check signals (`gemini_agrees_classification/_sentiment/_social_engineering`) as observability. Local results are never overridden; if Gemini is unavailable, the extractive summarizer takes over and everything else still works.

### 3. Conversation intelligence pipeline (Backend)

Support conversations → Backend `POST /api/v1/analyze` → Gemini conversation-level intelligence (category, sentiment, urgency, resolution state, summary, security signals, recommendation) → persisted to PostgreSQL (`analyses`, `threats`) → dashboard charts and conversation triage cards.

### 4. Security pipeline

Deterministic analyzers first (URL risk: IP hosts, shorteners, punycode, credential keywords; email risk: brand typosquatting, disposable domains, spoofing), social-engineering rule engine, then Gemini cross-check. Threats persist to the `threats` table and feed the Threats page + Security Analytics.

### 5. Serving & aggregation pipeline

Frontend consumes three origins: Data API (inbox/facets/dataset stats), Backend (conversations, reviews, dashboard, analytics, threats), and — for the inbox AI card — Backend `POST /reviews`, which fans out to the ML service. Dashboard overview merges live queue metrics with dataset-scale stats from the Data API (graceful degradation if it is down).

## Quick start

```bash
# One command for the whole local stack (health-gated, logs in .freebuff/logs/)
./run_dev.sh            # add --restart / --reset / --stop / --status as needed

# or Docker (5 containers: postgres + the 4 services above)
docker compose up --build
```

Requires `GEMINI_API_KEY` in `.env` (see `.env.example`) for summaries and cross-checks; everything else runs fully local.

## Testing

| Suite | Command |
|---|---|
| ML service (165 tests) | `cd app/ml_services && .venv/bin/python -m pytest tests/` |
| Backend | `cd app/Backend && uv run pytest` |
| Data service | `cd app/data && uv run pytest` |
| Frontend build | `cd app/frontend && npm run build` |

## Documentation map

| Document | Contents |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, all four pipelines in depth, data contracts between services |
| [`docs/api-contract.md`](docs/api-contract.md) | Audited Backend API surface (conversations, analysis, reviews, security, dashboard/analytics) |
| [`docs/ml-contract.md`](docs/ml-contract.md) | ML service API contract and canonical `CustomerReviewOutput` schema |
| [`docs/data-pipeline.md`](docs/data-pipeline.md) | Dataset profile, leakage controls, taxonomy mapping, preprocessing spec |
| [`docs/database-schema.md`](docs/database-schema.md) | PostgreSQL schema: conversations, messages, analyses, threats, customer_reviews |
| [`docs/known-limitations.md`](docs/known-limitations.md) | Honest constraints: dataset limits, model quality metrics |
| Module READMEs | [`app/ml_services`](app/ml_services/README.md) · [`app/Backend`](app/Backend/README.md) · [`app/data`](app/data/README.md) · [`app/frontend`](app/frontend/README.md) |
| Deployment | [`deploy/README-gcp.md`](deploy/README-gcp.md) (Cloud Run + Cloud SQL + Cloud Build) |
