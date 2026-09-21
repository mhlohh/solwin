# ML Service — Complaint & Security Intelligence

Production ML and security intelligence service powering complaint classification, clustering, urgency scoring, resolution tracking, action recommendations, security threat analysis, conversation summarization, and unified end-to-end analysis.

**Port:** `8000` · **Stack:** Python 3.11, FastAPI, scikit-learn (pinned via `constraints.txt`), Google Gemini

## Architecture: the tiered AI pipeline

Local ML/NLP is the **primary** tier; Gemini is **secondary** (summary-primary + cross-check). Every request therefore gets full triage at zero API cost in milliseconds, and classification can never be unavailable.

| Capability | Tier 1 — Local (always served) | Tier 2 — Gemini |
|---|---|---|
| Classification | TF-IDF + Logistic Regression, 11 canonical categories, `needs_review` abstention | agreement cross-check only |
| Sentiment | lexicon NLP engine (`sentiment/local_nlp.py`: phrase rules, negation, intensifiers) | agreement cross-check only |
| Social engineering | 9-rule regex engine (`security/social_engineering_detector.py`) | agreement cross-check only |
| Summary | extractive summarizer (fallback) | **primary** — abstractive |
| Urgency / resolution / recommendation / clustering / URL+email risk | deterministic engines | not used |

Gemini output never overrides local results; agreement signals (`gemini_agrees_*`) are observability only. If Gemini fails, the summary degrades to extractive and everything else is unaffected.

Deep dive: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — problems, solutions, per-subsystem walkthroughs with diagrams.

## API surface

| Method & Path | Purpose |
|---|---|
| `GET /health`, `GET /ready` | liveness; readiness gates on model registry |
| `GET /api/v1/models`, `GET /api/v1/capabilities` | registry metadata, capability boundary |
| `POST /api/v1/classify` | category + fine-grained intent + abstention |
| `POST /api/v1/cluster`, `/cluster/batch`, `GET /clusters` | MiniBatchKMeans assignment (15 clusters) |
| `GET /api/v1/analytics/frequency` | thread-safe frequency telemetry |
| `POST /api/v1/urgency`, `/resolution`, `/recommend` | deterministic triage engines |
| `POST /api/v1/url/analyze`, `/email/analyze` | URL risk (IP hosts, shorteners, punycode) and email risk (typosquat, disposable, spoof) |
| `POST /api/v1/summarize` | extractive (default) or LLM (`prefer_llm=true`) |
| `POST /api/v1/analyze` | unified pipeline → `UnifiedAnalysisResponse` |
| `POST /api/v1/analyze/batch` | batch unified analysis |
| `POST /api/v1/analyze/review` | **canonical `CustomerReviewOutput`** (13-section contract consumed by the Backend) |

## Local development

```bash
cd app/ml_services

# Run all tests (165 passing)
.venv/bin/python -m pytest tests/

# Lint / types
.venv/bin/ruff check .
.venv/bin/mypy src/

# Dev server
.venv/bin/uvicorn ml_service.main:app --reload --port 8000
```

Configuration is environment-based (see `.env.example` at repo root): `GEMINI_API_KEY`, `GEMINI_MODEL`, `MODEL_DIR`, `MODEL_CONFIDENCE_THRESHOLD`, etc.

## Models & training

Artifacts live in `models/` (joblib) with metrics in `models/classification_metrics.json` and the registry in `config/model_registry.yaml`. Retrain with:

```bash
.venv/bin/python scripts/train_classifier.py    # 4-candidate selection by weighted F1; upserts registry
.venv/bin/python scripts/train_clusterer.py     # MiniBatchKMeans over TF-IDF
.venv/bin/python scripts/evaluate.py            # regenerate test-split metrics from the artifact
```

Train/serve consistency is guaranteed by importing the canonical cleaner from `app/data/backend/clean_data.py` — the same normalization runs in ingestion and inference.

## Docker

Built from `Dockerfile` with `constraints.txt` pinning the exact sklearn/numpy/scipy/joblib versions the shipped artifacts were trained under (joblib pickles are not guaranteed to load or predict identically across sklearn minor versions); base image is `python:3.11-slim` to match the training interpreter. Models are baked into the image — no runtime mounts, Cloud Run compatible. Non-root user, healthcheck included.
