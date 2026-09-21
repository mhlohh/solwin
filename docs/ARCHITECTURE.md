# Solwin — System Architecture

> Central architecture reference: services, the four main pipelines, data contracts between services, and where every subsystem lives. Module-internal detail lives in each module's README and `app/ml_services/docs/ARCHITECTURE.md`.

## 1. High-level topology

```
                    ┌──────────────────────────────┐
                    │   Frontend  :5173 / :8080    │
                    │   React + Vite + Tailwind    │
                    └──────┬───────────┬───────────┘
                           │           │
             /data-api/*   │           │  /api/v1/*
                           ▼           ▼
        ┌──────────────────────┐   ┌───────────────────────────┐
        │  Data API  :8002     │   │  Backend API  :8001       │
        │  FastAPI (read-only) │   │  FastAPI + PostgreSQL     │
        └──────────┬───────────┘   └──────┬──────────┬─────────┘
                   │                      │          │
        inbox_dev.db / Postgres           │          │ ML_SERVICE_URL
        (20,862 cleaned records)          │          ▼
                                          │   ┌───────────────────────────┐
                                          └──►│  ML Service  :8000        │
                                              │  FastAPI + joblib models  │
                                              │  + Gemini (summary tier)  │
                                              └───────────────────────────┘
```

- The **frontend** talks to exactly one backend origin in production (nginx proxies `/api/v1/*` → Backend, `/data-api/*` → Data API). In dev, Vite does the same via its proxy.
- The **Backend** is the only writer of the operational DB (conversations, messages, analyses, threats, customer_reviews) and the only caller of the ML service for persisted analysis.
- The **Data API** is read-only at runtime: nothing writes back into the inbox dataset; AI enrichment for inbox records is persisted in the Backend DB keyed by `INBOX-<recordId>`.

## 2. Pipeline 1 — Ingestion (dataset → inbox)

```
unified_customer_phishing_data.csv (28,942 rows)
  → clean_data.py     NFKC normalize, trim, null/duplicate handling, complaint_text
  → priority.py       deterministic CRITICAL/HIGH/MEDIUM/LOW rule cascade
                      (phishing flag → technique → intent → issue → label)
  → seed.py           bulk insert (idempotent) into the inbox DB
  → Data API :8002    /tickets (20/page, priority-first FIFO), /tickets/{id},
                      /tickets/facets, /tickets/stats
```

Design properties: raw data is immutable; priority is never ML (auditable, reproducible); the API is read-only and horizontally scalable; a 20-row page answers in milliseconds. Detail: [`data-pipeline.md`](data-pipeline.md).

## 3. Pipeline 2 — AI inference (tiered, ML service)

```
                    ┌─────────────────────────────────────────────┐
 message/subject ──►│ TIER 1 · LOCAL (always runs, ms latency)    │
                    │  classification  TF-IDF + LogReg (11 cats,  │
                    │                  needs_review abstention)   │
                    │  sentiment       lexicon NLP (local_nlp.py) │
                    │  social eng.     9-rule regex engine        │
                    │  urgency         deterministic cascade      │
                    │  resolution      pattern state machine      │
                    │  recommendation  YAML business rules        │
                    │  clustering      MiniBatchKMeans TF-IDF     │
                    │  security        URL/email heuristic engines│
                    └──────────────┬──────────────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────────┐
                    │ TIER 2 · GEMINI (single structured call)    │
                    │  abstractive summary  ← primary role        │
                    │  gemini_agrees_classification               │
                    │  gemini_agrees_sentiment                    │
                    │  gemini_agrees_social_engineering           │
                    │  (observability only — never overrides)     │
                    └──────────────┬──────────────────────────────┘
                                   ▼
              CustomerReviewOutput (canonical 13-section schema)
```

Failure behavior: if Gemini is unavailable, the summary degrades to the extractive summarizer (`summary_fallback_extractive` warning) and Tier 1 results are unaffected — classification/sentiment/SE can never be unavailable. A deterministic guard routes CRITICAL-urgency + security-signal + unconfident-classify cases to `SECURITY_CONCERN` regardless of classifier output. Detail: [`../app/ml_services/docs/ARCHITECTURE.md`](../app/ml_services/docs/ARCHITECTURE.md) and [`ml-contract.md`](ml-contract.md).

## 4. Pipeline 3 — Conversation intelligence (Backend)

```
support conversation transcript
  → POST /api/v1/analyze            (frontend "Run AI analysis")
  → Gemini conversation-level call  (category, sentiment, urgency, resolution,
                                     summary, security signals, recommendation)
  → persisted: analyses + threats tables
  → feeds: conversation triage cards, dashboard KPIs, analytics charts,
           threat list
  → GET /api/v1/analyze/conversation/{id}   (cached persisted result)
```

Inbox records take a different path: the frontend fetches ticket text from the Data API, then calls Backend `POST /api/v1/reviews`, which fans out to the ML service tiered pipeline and caches the `CustomerReviewOutput` per `INBOX-<recordId>`.

## 5. Pipeline 4 — Serving & aggregation (Frontend)

| Page | Sources |
|---|---|
| Dashboard | Backend `/dashboard/overview` (merges queue metrics + Data API dataset stats, degrades gracefully) |
| Inbox | Data API `/tickets`, `/tickets/facets`; AI card via Backend `/reviews/INBOX-{id}` |
| Conversations | Backend `/conversations`, detail + triage + security card + composer |
| Threats | Backend `/security/threats`; "Dataset phishing" tab via Data API `/tickets?phishing=true` |
| Security Analytics | Backend `/analytics/security*` + Data API `/tickets/stats` (dataset-scale KPIs) |
| Customer Insights | Backend `/analytics/customer*` + Data API `/tickets/stats` |

## 6. Data contracts between services

| Contract | Producer → Consumer | Schema |
|---|---|---|
| `GET /tickets`, `/tickets/stats`, `/tickets/facets` | Data API → Frontend, Backend (dashboard merge) | ticket rows + pre-aggregated stats |
| `POST /api/v1/reviews` (request) | Frontend → Backend | flat: `source_record_id, domain, channel, subject, message` |
| `POST /api/v1/analyze` (ML) | Backend → ML service | `ComplaintInput` → tiered `CustomerReviewOutput` |
| `POST /api/v1/analyze` (conversation) | Frontend → Backend | conversation id → persisted intelligence |

Versioning rule: additive changes only; consumers must tolerate unknown fields. The canonical review schema is documented in [`ml-contract.md`](ml-contract.md) and implemented in both `app/ml_services/src/ml_service/api/schemas.py` and `app/Backend/app/schemas/review.py`.

## 7. Deployment topology

Local: `docker compose` (postgres + 4 services) or `./run_dev.sh` (venv processes). Cloud: Cloud Run + Cloud SQL, images built by Cloud Build into Artifact Registry — see [`../deploy/README-gcp.md`](../deploy/README-gcp.md). The ML image bakes model artifacts in (no runtime mount) and pins the exact sklearn/numpy environment via `constraints.txt` (joblib pickle compatibility).

## 8. Security model

- No authentication by design (hackathon scope); the `users` table exists but is not wired to endpoints.
- All customer content is treated as untrusted: prompt-injection delimiting around Gemini calls, instruction-never-executed policy for URLs/emails/attachments, security-critical tokens preserved verbatim for the analyzers.
- No secrets in code or logs; Gemini key flows only via environment.
