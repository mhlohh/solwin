# Master Feature Inventory & Reconciliation Audit

## 1. Overview
This document provides a feature-by-feature audit of all components across the Customer Complaint ML & Security Intelligence Platform (`Solwin`).

Statuses used:
- `REQUIRED`: Explicit core requirement, active and operational.
- `REQUIRED-BUT-BROKEN`: Core requirement with defect found and resolved during reconciliation.
- `OPTIONAL`: Valid complementary feature retained for operational excellence.
- `EXTRA`: Feature implemented beyond minimal specs; audited and safely retained.
- `UNSUPPORTED`: Hallucinated or non-compliant feature isolated/disabled.
- `CONFLICTING`: Feature with competing implementations, reconciled to canonical standard.

---

## 2. Feature Inventory Matrix

| Feature | Owner | Source Module | API Endpoint | DB Table | Frontend Dependency | Requirement Source | Test Coverage | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| **Complaint Classification (11 Categories)** | Team A (ML) | `ml_service/classification/classifier.py` | `POST /api/v1/classify` | `analyses.category` | Category filtering & badge | Canonical Business Taxonomy | Unit & QA (`test_qa_classification_and_abstention.py`) | `REQUIRED` | Predicts 11 canonical categories with probability calibration & abstention thresholding. |
| **Abstention Logic (`needs_review`)** | Team A (ML) | `ml_service/classification/classifier.py` | `POST /api/v1/classify` | `analyses` | Review flag queue | Anti-Hallucination & Model Safety | `test_qa_classification_and_abstention.py` | `REQUIRED` | Sets `needs_review=True` if confidence is below calibrated threshold. |
| **Fine-Grained Intent Classification (65 Classes)** | Team A (ML) | `ml_service/classification/classifier.py` | `POST /api/v1/classify` | `tickets.intent` | Intent breakdown | Raw Dataset Taxonomy | `test_qa_intents_and_clustering.py` | `OPTIONAL` | Predicts raw fine-grained intent mapped to canonical category. |
| **Semantic Topic Clustering (15 Clusters)** | Team A (ML) | `ml_service/clustering/clusterer.py` | `POST /api/v1/cluster`, `/batch` | `analyses` / telemetry | Cluster analytics & trends | Unsupervised grouping | `test_qa_intents_and_clustering.py` | `REQUIRED` | Centroid distance assignment against pre-computed cluster centroids with keyword extraction. |
| **Objective Urgency Scoring** | Team A (ML) | `ml_service/urgency/detector.py` | `POST /api/v1/urgency` | `analyses.priority` | Priority tagging | Operational Risk | `test_qa_analytics_urgency_recommendation.py` | `REQUIRED` | Maps operational signals (financial deduction, account takeover) to `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`. |
| **Factual Resolution Tracking** | Team A (ML) | `ml_service/resolution/detector.py` | `POST /api/v1/resolution` | `analyses.resolution_status` | Status badge | Resolution Intelligence | `test_qa_analytics_urgency_recommendation.py` | `REQUIRED` | Evidence-based fulfillment detection (`RESOLVED`, `UNRESOLVED`, `PARTIALLY_RESOLVED`, `UNKNOWN`). |
| **Security URL Analysis** | Team A (ML) | `ml_service/security/url_analyzer.py` | `POST /api/v1/url/analyze` | `threats.suspicious_urls` | Threat radar | Phishing & Threat Intelligence | `test_url_analyzer.py` | `REQUIRED` | Detects raw IP hosts, URL shorteners, punycode homoglyphs, and suspicious paths/TLDs. |
| **Security Email & Typosquatting Analysis** | Team A (ML) | `ml_service/security/email_analyzer.py` | `POST /api/v1/email/analyze` | `threats.suspicious_emails` | Threat radar | Phishing & Threat Intelligence | `test_email_analyzer.py` | `REQUIRED` | Detects disposable domains and lookalike brand typosquatting while preventing false positives on genuine domains (`google.com`). |
| **Action Recommendation Engine** | Team A (ML) | `ml_service/recommendation/engine.py` | `POST /api/v1/recommend` | `analyses.recommended_action` | Action button / route | Operational Routing | `test_qa_analytics_urgency_recommendation.py` | `REQUIRED` | Priority-ordered deterministic rules mapping category, urgency, and security risk to operational teams. |
| **Extractive & Pluggable Conversation Summarization** | Team A (ML) | `ml_service/summarization/summarizer.py` | `POST /api/v1/summarize` | `analyses.summary` | Summary card | Ticket Briefing | `test_qa_api_and_failures.py` | `REQUIRED` | Extracts Order IDs, amounts, dates, actions taken, and pending actions without hallucination. |
| **Unified Analysis Orchestration** | Team A (ML) | `ml_service/api/routes.py` | `POST /api/v1/analyze` | `analyses`, `threats` | Comprehensive Detail View | Unified Intelligence Pipeline | `test_end_to_end_integration.py` | `REQUIRED` | Coordinates classification, clustering, urgency, resolution, security, and recommendation in single request. |
| **Data Normalization & Leakage-Free Splitting** | Team C (Data) | `ml_service/preprocessing/dataset.py` | CLI (`profile_dataset.py`) | N/A | N/A | Data Quality Gate | `test_qa_data_pipeline_and_leakage.py` | `REQUIRED` | Groups normalized complaint text hashes into cohesive split allocations to guarantee 0% train/val/test leakage. |
| **Raw Dataset Deduplication & Seeding** | Team C (Data) | `app/data/backend/clean_data.py`, `seed.py` | Startup lifecycle | `tickets` | Seed verification | Dataset Ingestion | `clean_data.py` tests | `REQUIRED-BUT-BROKEN` | Fixed relative path resolution bug in `clean_data.py` to point accurately to `unified_customer_phishing_data (1).csv`. |
| **Backend REST Conversation Management** | Team B (Backend) | `app/api/v1/conversations.py` | `GET/POST /api/v1/conversations` | `conversations`, `messages` | Conversation inbox | Backend Core | `test_conversations_api.py` | `REQUIRED` | Full conversation lifecycle tracking with stable `CONV-XXXXXX` references and message history. |
| **Backend Secure Attachment Storage & MIME Validation** | Team B (Backend) | `app/services/attachments/validation.py` | `POST /api/v1/attachments/upload` | `attachments` | Attachment viewer | Attachment Handling | `test_attachments.py` | `REQUIRED-BUT-BROKEN` | Fixed Windows backslash path traversal sanitization bug on POSIX systems (`boot.ini`). |
| **Backend Threat Campaign Correlation Radar** | Team B (Backend) | `app/services/campaign/campaign_service.py` | `GET /api/v1/campaigns` | `campaigns`, `threats` | Campaign Radar Dashboard | Security Clustering | `test_campaigns.py` | `EXTRA` | Correlates recurring phishing threats sharing indicators into security campaigns. |
| **Backend Pre-Aggregated Dashboard Analytics** | Team B (Backend) | `app/services/analytics_service.py` | `GET /api/v1/dashboard/overview`, `/analytics/customer` | `conversations`, `analyses` | Dashboard KPIs | Analytics & Reporting | `test_analytics.py` | `REQUIRED` | Computes aggregated category breakdown, sentiment distribution, urgency, and resolution stats. |
| **Live Mailbox Integration (IMAP/SMTP/OAuth)** | Hallucinated / Deprecated | N/A | N/A | N/A | N/A | Out of Scope | N/A | `UNSUPPORTED` | Confirmed 0% live mailbox code present. Project is 100% dataset-driven. |
| **Hardcoded Gemini API Dependency** | Team B (Backend) | `app/services/ai/customer_intelligence.py` | `POST /api/v1/analyze` | N/A | N/A | In-process ML Integration | `test_customer_intelligence.py` | `CONFLICTING` | Reconciled: Backend now integrates with canonical ML Service `POST /api/v1/analyze` and provides offline fallback when `GEMINI_API_KEY` is not set. |
