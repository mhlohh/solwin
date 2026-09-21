# Solwin — AI-Powered Customer Support Intelligence & Security Platform

Solwin is an integrated enterprise customer intelligence and security platform that analyzes inbound customer communications, classifies complaints into canonical business taxonomies, detects security threats (phishing, social engineering, malicious URLs, credential harvesting), evaluates urgency, and delivers actionable recommendations for customer support operations.

---

## Architecture Overview

The system is strictly **dataset-driven** and structured into decoupled, independently testable services:

```
RAW DATASET (unified_customer_phishing_data.csv)
       ↓
DATA PREPROCESSING & CLEANING (app/data/backend)
       ↓
ML ORCHESTRATOR SERVICE (app/ml_services) [POST /api/v1/analyze]
       ↓
CANONICAL ML INTELLIGENCE RESULT (JSON)
       ↓
BACKEND REST API & PERSISTENCE (app/Backend) [FastAPI + SQLite/PostgreSQL]
       ↓
OPERATIONAL DASHBOARDS & CLIENTS
```

### Component Ownership
- **Team A — ML Service (`app/ml_services/`):** FastText & TF-IDF classification, MiniBatchKMeans clustering, urgency scoring, resolution analysis, security intelligence (URL/email homoglyph & spoofing analysis), social engineering rule engine, and master orchestrator.
- **Team B — Backend (`app/Backend/`):** FastAPI application, SQLAlchemy ORM models, attachment security validation, RBAC, complaint persistence, and REST endpoints.
- **Team C — Data Service (`app/data/`):** Raw dataset integrity protection, normalization, deduplication, and split leakage controls.
- **Team D — Frontend (`app/frontend/`):** Frontend interface contract documented in `docs/api-contract.md`.

---

## Canonical Complaint Taxonomy

All customer communications are mapped deterministically to the **11 Canonical Public Business Categories**:
1. `PAYMENT_TRANSACTION_ISSUE`
2. `ACCOUNT_LOGIN_PROBLEM`
3. `PRODUCT_ISSUE`
4. `DELIVERY_SHIPPING_PROBLEM`
5. `REFUND_REQUEST`
6. `SUBSCRIPTION_ISSUE`
7. `TECHNICAL_PROBLEM`
8. `SERVICE_QUALITY`
9. `BILLING_PROBLEM`
10. `SECURITY_CONCERN`
11. `OTHER`

---

## Quickstart & Verification

### 1. Run Baseline & Integration Tests
**ML Service Tests (114 passing):**
```bash
cd app/ml_services
.venv/bin/pytest -v
```

**Backend Tests (152 passing, including End-to-End integration):**
```bash
cd app/Backend
.venv/bin/pytest -v
```

### 2. Static Analysis & Type Checking
```bash
# ML Service
cd app/ml_services
.venv/bin/ruff check .
.venv/bin/mypy src/ml_service

# Backend
cd app/Backend
.venv/bin/ruff check .
```

### 3. Run Dataset Inference
Process records from the immutable raw dataset through the ML intelligence orchestrator:
```bash
cd app/ml_services
.venv/bin/python scripts/run_inference.py --input ../data/unified_customer_phishing_data\ \(1\).csv --limit 100
```

### 4. Start Services Locally
**Start ML Service:**
```bash
cd app/ml_services
.venv/bin/uvicorn ml_service.api.app:app --host 0.0.0.0 --port 8000 --reload
```

**Start Backend Service:**
```bash
cd app/Backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Documentation Index

- [Integration Architecture](docs/integration-architecture.md)
- [Feature Inventory & Status](docs/feature-inventory.md)
- [ML Intelligence Contract](docs/ml-contract.md)
- [Backend REST API Contract](docs/api-contract.md)
- [Database Schema Specification](docs/database-schema.md)
- [Data Pipeline & Leakage Controls](docs/data-pipeline.md)
- [Integration Decisions Log](docs/integration-decisions.md)
- [Pre-Integration Test Report](docs/pre-integration-test-report.md)
- [Post-Integration Test Report](docs/post-integration-test-report.md)
- [End-to-End Integration Test Report](docs/integration-test-report.md)
- [Known Limitations & Quality Gate](docs/known-limitations.md)