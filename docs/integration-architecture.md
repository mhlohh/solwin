# Integration Architecture & System Overview

## 1. High-Level Architecture

The Customer Complaint ML & Security Intelligence Platform (`Solwin`) is structured as a modular, dataset-driven intelligence system integrating data preprocessing, ML/security analytics, persistent backend services, and dashboard visualization.

```mermaid
flowchart TD
    subgraph Data Tier
        RAW[Raw Dataset CSV: unified_customer_phishing_data] --> PRE[Data Cleaning & Deduplication: clean_data.py]
        PRE --> SPLIT[Leak-Free Stratified Splitting: dataset.py]
        SPLIT --> TRAIN[Model Training & Quality Gate: train_classifier.py]
    end

    subgraph ML Service Tier - Port 8000
        TRAIN --> REG[Model Registry: models/]
        REG --> ORCH[Unified Orchestrator: POST /api/v1/analyze]
        
        ORCH --> CLF[1. Calibrated Classification: 11 Categories]
        ORCH --> CLU[2. Topic Clustering: 15 Centroids]
        ORCH --> URG[3. Objective Urgency Detector: LOW..CRITICAL]
        ORCH --> RES[4. Factual Resolution Detector]
        ORCH --> SEC[5. Threat Intelligence: URL/Email Scanner]
        ORCH --> REC[6. Action Recommendation Engine]
        ORCH --> SUM[7. Extractive Summarizer]
    end

    subgraph Backend Service Tier - Port 8001
        ORCH --> B_INGEST[Unified Intelligence Service]
        B_INGEST --> DB[(PostgreSQL Database)]
        
        DB --> TBL_CONV[conversations]
        DB --> TBL_MSG[messages]
        DB --> TBL_ANALYSIS[analyses]
        DB --> TBL_THREAT[threats]
        DB --> TBL_ATTACH[attachments]
        DB --> TBL_CAMP[campaigns]
        
        DB --> B_API[Backend REST API /api/v1/]
        B_API --> DASH[GET /dashboard/overview]
        B_API --> ANALYTICS[GET /analytics/customer]
        B_API --> CONVS[GET /conversations]
    end

    subgraph Frontend Tier - Planned Contract
        DASH --> UI_KPI[KPI Metrics & Status Counts]
        ANALYTICS --> UI_CHARTS[Category & Urgency Distributions]
        CONVS --> UI_LIST[Ticket Inbox & Security Detail Radar]
    end
```

---

## 2. Component Boundaries & Responsibilities

### Team A: ML Service (`app/ml_services`)
- **Port**: `8000`
- **Ownership**:
  - Model weights, feature extraction pipelines, vocabulary dictionaries.
  - Zero-leakage inference engine.
  - Objective urgency scoring and factual resolution detection.
  - URL and email threat intelligence scanning.
  - Priority-ordered deterministic action recommendation.
  - Extractive summarization with zero hallucination.
  - Serves canonical API: `POST /api/v1/analyze`.

### Team B: Backend Service (`app/Backend`)
- **Port**: `8001`
- **Ownership**:
  - Relational schema management (SQLAlchemy ORM + Alembic).
  - Conversation lifecycle and message persistence.
  - Strict MIME validation and secure filesystem attachment storage.
  - Automated threat campaign correlation across shared indicators.
  - Analytical aggregation queries for dashboard rendering.
  - Client authentication and role-based access control (`RBAC`).

### Team C: Data Engineering (`app/data`)
- **Ownership**:
  - Source raw dataset preservation (`unified_customer_phishing_data (1).csv`).
  - Automated data cleaning, whitespace normalization, and deduplication (`clean_data.py`).
  - Automated database seeding (`seed.py`).

### Team D: Frontend Contract (`app/frontend`)
- **Status**: Absent in current checkout (`.gitkeep`).
- **Integration**: Fully specified in `docs/api-contract.md` to consume Backend REST endpoints without modification.
