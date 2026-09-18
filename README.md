# Customer Complaint Intelligence — ML Services

A modular FastAPI service that will turn customer complaints and support conversations into structured intelligence. The first delivery establishes the API, configuration, privacy controls, model registry, Docker image, and CI foundation. It intentionally does **not** claim a trained model: the required dataset has not yet been supplied to this repository or workspace.

## Architecture

```text
Backend -> FastAPI gateway -> preprocessing -> classifier / clustering / urgency /
resolution / security analysis / summarization -> unified response
```

The components are implemented in phases. Phase 1 is runnable operations infrastructure; Phases 2–8 add reproducible data profiling, training, inference, and analysis modules without retraining at API startup.

## Current capabilities

- `GET /health` — liveness check
- `GET /ready` — readiness check; returns 503 until a production model is registered
- `GET /api/v1/models` — model metadata from the registry
- `GET /api/v1/capabilities` — implemented versus planned capability boundary
- `GET /docs`, `/redoc`, and `/openapi.json` — generated API documentation

## Local development

Requires Python 3.11–3.13.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
uvicorn ml_service.main:app --reload
pytest
```

Copy `.env.example` to `.env`; do not commit it. Configuration, model locations, thresholds, and external-provider credentials are environment based.

## Docker

```bash
docker compose up --build
curl http://localhost:8000/health
```

The image uses a non-root user, includes no secrets, mounts models read-only, and checks liveness without requiring a trained model.

## Dataset and training

The prescribed CSV, `unified_customer_phishing_data_subset (1).csv`, is not currently available. Before training, Phase 2 will validate its schema and encoding; profile missing values, duplicates, label distribution, text lengths, and leakage; inspect `issue` for label leakage; define an explicit intent-to-category mapping; create stratified splits; and save reproducible reports.

Training will be invoked explicitly with `python scripts/train_classifier.py`; it will never run at API startup. Metrics, calibration results, artifact paths, and metadata will be placed in the model registry. No production frequency is inferred from training data.

## Security and privacy

Raw customer content, full email addresses, tokens, passwords, and credentials are excluded from service logs. External URL/email reputation providers and any LLM summarizer will be optional interfaces with timeouts; deterministic processing remains available if they are unavailable.

## CI

Every ML-code PR runs formatting, lint, type checks, unit/API tests, and a Docker build. Model training stays out of PR CI; a lightweight model smoke test will be added with the first persisted artifact.

## Next phase

Supply the CSV securely (do not commit unapproved customer data), then implement profiling, preprocessing, leakage checks, the mapping review, and classifier evaluation. See `AGENTS.md` for review priorities and `docs/PR_REVIEW.md` for the pull-request process.
