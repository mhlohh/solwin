# Final API Inventory

This document defines the audited and approved API surface for the **Customer Complaint ML & Security Intelligence Platform** following the removal of unsupported/hallucinated features (Campaigns, Attachments/Multimodal, and redundant ML-layer analytics).

---

## 1. ML Service (`ml_service` on port 8001)

The ML service is strictly an inference engine. It does not handle authentication, persistent database CRUD, or application-level analytics dashboards.

| Endpoint | Method | Owner | Purpose | Used By | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/health` | GET | ML Service | Liveness check & loaded model status | Health probes / Orchestrator | **REQUIRED** |
| `/ready` | GET | ML Service | Readiness verification confirming all models loaded | Health probes / Orchestrator | **REQUIRED** |
| `/api/v1/models` | GET | ML Service | Inspect registered model names and versions | Admin / Model Registry inspect | **REQUIRED** |
| `/api/v1/capabilities` | GET | ML Service | Returns list of active operational ML capabilities | Operations / Monitoring | **REQUIRED** |
| `/api/v1/analyze` | POST | ML Service | **Primary ML Endpoint**: Unified complaint analysis pipeline (Classification, Intent, Urgency, Resolution, Security, Recommendations, Summary) | Backend `UnifiedIntelligenceService` | **REQUIRED** |
| `/api/v1/analyze/batch` | POST | ML Service | **Batch ML Endpoint**: High-throughput complaint batch processing for datasets | Dataset Ingestion / Bulk Pipeline | **REQUIRED** |
| `/api/v1/classify` | POST | ML Service | Single complaint business category classification | ML Developer Testing | **INTERNAL** |
| `/api/v1/cluster` | POST | ML Service | Single complaint vector clustering assignment | ML Developer Testing | **INTERNAL** |
| `/api/v1/cluster/batch` | POST | ML Service | Batch complaint vector clustering | ML Developer Testing | **INTERNAL** |
| `/api/v1/clusters` | GET | ML Service | List active topic clusters and top terms | ML Developer Testing | **INTERNAL** |
| `/api/v1/analytics/frequency` | GET | ML Service | Rolling frequency tracking for complaint categories | ML Developer Testing | **INTERNAL** |
| `/api/v1/urgency` | POST | ML Service | Urgency level detection (LOW, MEDIUM, HIGH, CRITICAL) | ML Developer Testing | **INTERNAL** |
| `/api/v1/resolution` | POST | ML Service | Resolution status detection (Resolved, In-Progress, Pending) | ML Developer Testing | **INTERNAL** |
| `/api/v1/recommend` | POST | ML Service | Action recommendation rule engine output | ML Developer Testing | **INTERNAL** |
| `/api/v1/url/analyze` | POST | ML Service | URL cyber threat extraction, reputation & heuristics | ML Developer Testing | **INTERNAL** |
| `/api/v1/email/analyze` | POST | ML Service | Email header spoofing & lookalike domain detection | ML Developer Testing | **INTERNAL** |
| `/api/v1/summarize` | POST | ML Service | Extractive & LLM complaint summarizer | ML Developer Testing | **INTERNAL** |
| `/api/v1/auth/*` | ALL | — | Application-level authentication | — | **REMOVED** (Never in ML) |
| `/api/v1/conversations/*` | ALL | — | Application-level conversation CRUD | — | **REMOVED** (Never in ML) |
| `/api/v1/attachments/*` | ALL | — | File storage / Multimodal image OCR | — | **REMOVED** (Out of scope) |
| `/api/v1/campaigns/*` | ALL | — | Campaign tracking & correlation | — | **REMOVED** (Out of scope) |
| `/api/v1/dashboard/*` | ALL | — | Dashboard metrics aggregation | — | **REMOVED** (Backend owns this) |
| `/api/v1/analytics/customer/*` | ALL | — | Customer analytics queries | — | **REMOVED** (Backend owns this) |
| `/api/v1/analytics/security/*` | ALL | — | Security analytics queries | — | **REMOVED** (Backend owns this) |

---

## 2. Backend Application API (`Backend` on port 8000)

The Backend API coordinates PostgreSQL persistence, JWT authentication, ticket management, operational dashboards, and communicates with the ML Service for intelligence.

| Endpoint | Method | Owner | Purpose | Used By | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/health` | GET | Backend API | Liveness health check | Health probes / Load balancer | **REQUIRED** |
| `/api/v1/auth/login` | POST | Backend Auth | JWT Bearer OAuth2 authentication | Frontend Login UI | **REQUIRED** |
| `/api/v1/auth/me` | GET | Backend Auth | Current authenticated user profile | Frontend AuthContext / User State | **REQUIRED** |
| `/api/v1/conversations` | GET | Backend Conversations | Paginated listing of customer complaint tickets | Frontend Conversation List | **REQUIRED** |
| `/api/v1/conversations` | POST | Backend Conversations | Create new complaint ticket record | Ingestion / Agent UI | **REQUIRED** |
| `/api/v1/conversations/{id}` | GET | Backend Conversations | Full conversation detail with message history | Frontend Conversation Detail View | **REQUIRED** |
| `/api/v1/conversations/{id}` | PATCH | Backend Conversations | Update conversation status or assigned agent | Agent workflow | **REQUIRED** |
| `/api/v1/conversations/{id}` | DELETE | Backend Conversations | Delete conversation record | Admin workflow | **REQUIRED** |
| `/api/v1/conversations/{id}/messages` | GET | Backend Conversations | Retrieve ordered message timeline | Frontend Timeline | **REQUIRED** |
| `/api/v1/conversations/{id}/messages` | POST | Backend Conversations | Append a message to a ticket | Frontend / Customer replies | **REQUIRED** |
| `/api/v1/security/analyze` | POST | Backend Security | Ad-hoc security text evaluation | SOC Analyst tools | **REQUIRED** |
| `/api/v1/security/conversation/{id}` | GET | Backend Security | Persisted security intelligence record | Frontend Threat Detail View | **REQUIRED** |
| `/api/v1/analyze` | POST | Backend Unified | Trigger full unified intelligence pipeline | Frontend Analyze Trigger | **REQUIRED** |
| `/api/v1/analyze/message` | POST | Backend Unified | Direct message unified analysis | Live Ingestion / Testing | **REQUIRED** |
| `/api/v1/analyze/conversation/{id}` | GET | Backend Unified | Get latest persisted unified analysis | Frontend AI Insight Panels | **REQUIRED** |
| `/api/v1/dashboard/overview` | GET | Backend Dashboard | Pre-aggregated KPI summary metrics | Frontend Dashboard Overview | **REQUIRED** |
| `/api/v1/analytics/customer` | GET | Backend Analytics | Sentiment & top issues metrics | Frontend Customer Insights Page | **REQUIRED** |
| `/api/v1/analytics/customer/top-issues` | GET | Backend Analytics | Category volume frequency breakdown | Frontend Customer Insights Page | **REQUIRED** |
| `/api/v1/analytics/customer/trends` | GET | Backend Analytics | Historical complaint volume trends | Frontend Customer Insights Page | **REQUIRED** |
| `/api/v1/analytics/security` | GET | Backend Analytics | SIEM-style security risk distributions | Frontend Security Metrics Page | **REQUIRED** |
| `/api/v1/analytics/security/recent-threats` | GET | Backend Analytics | Recent critical threats feed | SOC Live Alerts | **REQUIRED** |
| `/api/v1/analytics/security/trends` | GET | Backend Analytics | Time-series threat volume breakdown | Frontend Security Metrics Page | **REQUIRED** |
| `/api/v1/campaigns` | GET | Backend Campaigns | Adversary campaign aggregation | — | **REMOVED** |
| `/api/v1/campaigns/{id}` | GET | Backend Campaigns | Adversary campaign detail | — | **REMOVED** |
| `/api/v1/campaigns/{id}/status` | PATCH | Backend Campaigns | Adversary campaign lifecycle status | — | **REMOVED** |
| `/api/v1/campaigns/radar` | GET | Backend Campaigns | Multi-wave campaign telemetry radar | — | **REMOVED** |
| `/api/v1/conversations/{c_id}/messages/{m_id}/attachments` | POST | Backend Attachments | Upload message attachment | — | **REMOVED** |
| `/api/v1/attachments/{id}` | GET | Backend Attachments | Retrieve attachment by ID | — | **REMOVED** |
| `/api/v1/attachments/{id}` | DELETE | Backend Attachments | Delete stored attachment | — | **REMOVED** |
| `/api/v1/analysis/multimodal` | POST | Backend AI | Multimodal vision & OCR processing | — | **REMOVED** |

---

## 3. Architecture Summary

```
                 FRONTEND (Vite / React SPA)
                            │
                            ▼
                    BACKEND API (:8000)
    (Auth, Conversations, PostgreSQL, Dashboard, Analytics)
                            │
                            │ POST /api/v1/analyze
                            │ POST /api/v1/analyze/batch
                            ▼
                    ML SERVICE (:8001)
     (Unified Intelligence Pipeline, Deterministic Security,
      NLP Intent, Urgency, Resolution, Recommendations)
```
