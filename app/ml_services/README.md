# Customer Complaint Intelligence ML Service

Production-grade ML and Security Intelligence Service powering AI-driven complaint classification, clustering, urgency scoring, resolution tracking, action recommendations, security threat extraction, conversation summarization, and unified end-to-end analysis.

## Capabilities

- **Complaint Classification (`POST /api/v1/classify`)**: Calibrated multi-class classification into 11 canonical business categories (`PAYMENT_ISSUE`, `DELIVERY_PROBLEM`, `FRAUD_DISPUTE`, `ACCOUNT_ACCESS`, etc.) and 65 fine-grained intents with abstention thresholds (`needs_review`).
- **Topic Clustering & Frequency Analytics (`POST /api/v1/cluster`, `POST /api/v1/cluster/batch`, `GET /api/v1/clusters`, `GET /api/v1/analytics/frequency`)**: Centroid distance cluster assignment across 15 semantic clusters, keyword extraction, and thread-safe real-time frequency telemetry.
- **Urgency Detection (`POST /api/v1/urgency`)**: Objective urgency assessment (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) using business-logic signals (fraud indicators, account takeovers, payment failures) rather than subjective sentiment or anger.
- **Resolution Tracking (`POST /api/v1/resolution`)**: Factual resolution status detection (`RESOLVED`, `UNRESOLVED`, `PARTIALLY_RESOLVED`, `UNKNOWN`) based on objective settlement and delivery milestones.
- **Action Recommendations (`POST /api/v1/recommend`)**: Prioritized deterministic action recommendations (`config/action_rules.yaml`) routing complaints to relevant support, billing, fraud, or technical teams.
- **Security Intelligence (`POST /api/v1/url/analyze`, `POST /api/v1/email/analyze`)**: Deterministic URL/domain risk scoring (IP hosts, shorteners, punycode, credential keywords) and email intelligence (brand typosquatting, disposable domains, spoof detection).
- **Conversation Summarization (`POST /api/v1/summarize`)**: Extractive entity recognition (Order IDs, amounts, dates, emails, phones), customer issue synthesis, actions taken, and pending items, with pluggable external LLM support.
- **Unified Master Pipeline (`POST /api/v1/analyze`)**: Single-call orchestration aggregating classification, clustering, telemetry, urgency, resolution, recommendations, security scanning, and summarization with partial failure tolerance.
- **Operations (`GET /health`, `GET /ready`, `GET /api/v1/capabilities`, `GET /api/v1/models`)**: Liveness, readiness tied to model registry status, and capability discovery.

## Local Development & Validation

```bash
cd app/ml_services

# Run all tests (71 passed)
uv run pytest

# Lint and formatting check
uv run ruff check .

# Static type checking across all 52 source files
uv run mypy src/ scripts/ tests/

# Run dev server
uv run uvicorn ml_service.main:app --reload --port 8000
```

## Docker Deployment

```bash
docker compose up --build
```
The service runs with a non-root user (`app`), read-only container filesystem, tmpfs `/tmp`, and built-in container healthchecks.
