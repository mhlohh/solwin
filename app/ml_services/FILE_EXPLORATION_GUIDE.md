# ML Service Codebase Architecture & File Reference Guide

This document provides a comprehensive per-file reference of the `app/ml_services` service. It outlines each directory, configuration file, source module, script, test suite, and report for easy exploration and future reference.

---

## 1. Top-Level Project Files

| File | Purpose | Description |
|---|---|---|
| [`pyproject.toml`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/pyproject.toml) | Dependency & Project Metadata | Defines the Python environment (`uv`, hatchling build backend), dependencies (`fastapi`, `scikit-learn`, `pydantic`, `pyyaml`, `pandas`, `joblib`, etc.), and tool configurations (`ruff`, `mypy`, `pytest`). |
| [`uv.lock`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/uv.lock) | Lockfile | Hermetic lockfile pinning dependencies and transitive packages for deterministic reproducible builds. |
| [`Dockerfile`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/Dockerfile) | Container Build Definition | Multi-stage Docker build producing a secure, non-root (`app`), read-only root filesystem container with `/tmp` tmpfs mount and built-in healthchecks. |
| [`docker-compose.yml`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/docker-compose.yml) | Container Orchestration | Local deployment configuration exposing port 8000, setting environment variables, and establishing container healthchecks. |
| [`README.md`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/README.md) | Service Overview | High-level summary of capabilities, API endpoints, testing instructions, and docker commands. |
| [`FILE_EXPLORATION_GUIDE.md`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/FILE_EXPLORATION_GUIDE.md) | Exploration Guide | This comprehensive file-by-file reference guide. |

---

## 2. Configuration (`config/`)

Declarative YAML configurations that govern ML thresholds, business rules, and models.

| File | Purpose | Key Contents |
|---|---|---|
| [`config/action_rules.yaml`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/config/action_rules.yaml) | Decision & Escalation Rules | Priority-ordered declarative rules matching `category`, `urgency`, `security_risk`, and `resolution` to primary/secondary actions (e.g. `RULE_SECURITY_INCIDENT`, `RULE_ACCOUNT_TAKEOVER`, `RULE_CRITICAL_SECURITY_ESCALATION`, `RULE_PAYMENT_FRAUD_CRITICAL`). |
| [`config/intent_category_mapping.yaml`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/config/intent_category_mapping.yaml) | Taxonomy & Intent Mapping | Maps 65 fine-grained intent labels to 11 canonical business categories (`PAYMENT_TRANSACTION_ISSUE`, `DELIVERY_SHIPPING_PROBLEM`, `SECURITY_CONCERN`, etc.). |
| [`config/model_config.yaml`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/config/model_config.yaml) | Hyperparameters & Feature Config | Feature extraction parameters (n-gram ranges, sublinear TF-IDF, max features) and abstention thresholds for classification and clustering. |
| [`config/model_registry.yaml`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/config/model_registry.yaml) | Model Manifest | Tracks deployed models, versions, artifact locations, framework types, loaded state, and verification checksums. |

---

## 3. Application Source Code (`src/ml_service/`)

The core application code organized into modular micro-components.

### Application Root
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/main.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/main.py) | Application Entrypoint | FastAPI application factory, lifespan management (initializes registry, models, analyzers, frequency tracker), middleware (request logging, timing, CORS), and global exception handlers. |
| [`src/ml_service/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/__init__.py) | Package Init | Top-level package marker for `ml_service`. |

### Core Subpackage (`src/ml_service/core/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/core/logging.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/core/logging.py) | Secure Structured Logging | `safe_log()` function with recursive data sanitization. Redacts PAN card numbers, JWT tokens, Bearer authorizations, emails, API keys, and sensitive dictionary fields across arbitrary nested structures. |
| [`src/ml_service/core/config.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/core/config.py) | Environment & Settings | Pydantic `Settings` model reading environment variables (paths, log levels, security thresholds, host/port). |
| [`src/ml_service/core/model_registry.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/core/model_registry.py) | Model Lifecycle & Health | Reads `config/model_registry.yaml`, verifies file presence, tracks model health status, and exposes registered model metadata. |
| [`src/ml_service/core/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/core/__init__.py) | Package Init | Exports logging, config, and registry utilities. |

### API Layer (`src/ml_service/api/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/api/routes.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/api/routes.py) | REST API Endpoints | Implements FastAPI endpoints: `/health`, `/ready`, `/api/v1/classify`, `/api/v1/cluster`, `/api/v1/cluster/batch`, `/api/v1/clusters`, `/api/v1/analytics/frequency`, `/api/v1/urgency`, `/api/v1/resolution`, `/api/v1/recommend`, `/api/v1/url/analyze`, `/api/v1/email/analyze`, `/api/v1/summarize`, and unified `/api/v1/analyze`. |
| [`src/ml_service/api/schemas.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/api/schemas.py) | Pydantic Data Models & Enums | Canonical enums (`BusinessCategory`, `UrgencyLevel`, `ResolutionStatus`, `ActionType`, `SecurityRiskLevel`) and request/response models for all endpoints. |
| [`src/ml_service/api/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/api/__init__.py) | Package Init | Exports schemas and routes. |

### Preprocessing (`src/ml_service/preprocessing/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/preprocessing/cleaner.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/preprocessing/cleaner.py) | Text Normalization | Cleans text, standardizes whitespace, combines subject and message (`build_complaint_text`), and strips non-printable characters. |
| [`src/ml_service/preprocessing/dataset.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/preprocessing/dataset.py) | Leak-Free Dataset Splitting | Ingests raw data, computes deterministic text hashes, and groups duplicate texts into single splits to guarantee 0% data leakage between train, val, and test. |
| [`src/ml_service/preprocessing/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/preprocessing/__init__.py) | Package Init | Exports text cleaner and dataset preparation functions. |

### Classification (`src/ml_service/classification/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/classification/classifier.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/classification/classifier.py) | Category & Intent Inference | Wraps the trained pipeline (`joblib`), produces calibrated class probabilities, computes prediction confidence, and flags `needs_review` when confidence is below the abstention threshold. |
| [`src/ml_service/classification/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/classification/__init__.py) | Package Init | Exports `ComplaintClassifier`. |

### Topic Clustering (`src/ml_service/clustering/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/clustering/clusterer.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/clustering/clusterer.py) | Semantic Topic Assignment | Maps complaints to nearest centroid, calculates distance to center, looks up topic names and keywords from `models/clusters_metadata.json`, and supports single and batch operations. |
| [`src/ml_service/clustering/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/clustering/__init__.py) | Package Init | Exports `ComplaintClusterer`. |

### Urgency Detection (`src/ml_service/urgency/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/urgency/detector.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/urgency/detector.py) | Objective Urgency Scoring | Evaluates business loss, unauthorized transactions, account compromise, and deadlines (e.g. `\burgent(ly)?\b`, `money was deducted`) into `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW` urgency without confusing angry sentiment with operational risk. |
| [`src/ml_service/urgency/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/urgency/__init__.py) | Package Init | Exports `UrgencyDetector`. |

### Resolution Detection (`src/ml_service/resolution/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/resolution/detector.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/resolution/detector.py) | Ticket Resolution Status | Detects whether a complaint is `RESOLVED`, `UNRESOLVED`, `PARTIALLY_RESOLVED`, or `UNKNOWN` based on factual delivery and refund outcomes. |
| [`src/ml_service/resolution/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/resolution/__init__.py) | Package Init | Exports `ResolutionDetector`. |

### Action Recommendation (`src/ml_service/recommendation/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/recommendation/engine.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/recommendation/engine.py) | Rule-Based Action Routing | Reads `config/action_rules.yaml`, sorts by ascending priority, evaluates condition criteria against complaint attributes, and returns primary/secondary recommended operational actions. |
| [`src/ml_service/recommendation/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/recommendation/__init__.py) | Package Init | Exports `RecommendationEngine`. |

### Security Intelligence (`src/ml_service/security/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/security/url_analyzer.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/security/url_analyzer.py) | URL Threat Intelligence | Extracts URLs from text, detects IP hostnames, punycode homoglyphs, suspicious TLDs, and path keywords; enforces configurable minimum risk (`shortener_min_risk`) for URL shorteners (`bit.ly`, `tinyurl.com`). |
| [`src/ml_service/security/email_analyzer.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/security/email_analyzer.py) | Email & Domain Threat Intelligence | Extracts email addresses, checks disposable domains, authentic brand exact matches (preventing Google false positives), and detects typosquatting/lookalike domain variations. |
| [`src/ml_service/security/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/security/__init__.py) | Package Init | Exports `URLAnalyzer` and `EmailAnalyzer`. |

### Conversation Summarization (`src/ml_service/summarization/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/summarization/summarizer.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/summarization/summarizer.py) | Entity & Issue Synthesis | Deterministic regex entity extraction (tracking numbers, amounts, dates, emails, phones), customer problem extraction, actions taken, and pending items. Supports pluggable LLM backends. |
| [`src/ml_service/summarization/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/summarization/__init__.py) | Package Init | Exports `ConversationSummarizer`. |

### Analytics (`src/ml_service/analytics/`)
| File | Purpose | Description |
|---|---|---|
| [`src/ml_service/analytics/frequency.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/analytics/frequency.py) | Real-Time Telemetry Tracker | Thread-safe in-memory rolling window frequency tracker recording category and cluster events, computing volume trends and velocity anomalies. |
| [`src/ml_service/analytics/__init__.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/src/ml_service/analytics/__init__.py) | Package Init | Exports `FrequencyTracker`. |

---

## 4. Scripts (`scripts/`)

Standalone operational and training scripts.

| File | Purpose | Description |
|---|---|---|
| [`scripts/profile_dataset.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/scripts/profile_dataset.py) | Dataset Profiling | Analyzes raw input CSV, detects duplicates, missing values, class distributions, and generates `dataset_profile_report.json`. |
| [`scripts/train_classifier.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/scripts/train_classifier.py) | Classifier Training | Trains TF-IDF + Calibrated LinearSVC classifier using `train.csv` and `val.csv`, saves artifact to `models/complaint_classifier_v1.joblib`, and outputs metrics to `models/classification_metrics.json`. |
| [`scripts/train_clusterer.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/scripts/train_clusterer.py) | Clusterer Training | Trains MiniBatchKMeans with domain conversational stop-words, saves cluster model to `models/clusterer_v1.joblib`, and writes cluster topic names and keywords to `models/clusters_metadata.json`. |
| [`scripts/evaluate.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/scripts/evaluate.py) | Evaluation Script | Evaluates serialized models against holdout test datasets and prints detailed classification metrics. |
| [`scripts/qa_benchmarks.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/scripts/qa_benchmarks.py) | QA Latency & Throughput Benchmark | Measures startup time, inference latency percentiles (p50, p95, p99), memory usage (RSS), and concurrency throughput (10, 50, 100 concurrent requests). |

---

## 5. Tests (`tests/`)

Full test suite with 100% pass rate (107 tests).

### Unit Tests (`tests/unit/`)
| File | Target Tested | Focus Areas |
|---|---|---|
| [`tests/unit/test_analytics.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_analytics.py) | `FrequencyTracker` | Event recording, rolling windows, velocity calculations, thread concurrency. |
| [`tests/unit/test_classifier.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_classifier.py) | `ComplaintClassifier` | Input parsing, confidence scoring, abstention threshold triggers. |
| [`tests/unit/test_clustering.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_clustering.py) | `ComplaintClusterer` | Centroid distance, topic assignment, metadata keywords, batch clustering. |
| [`tests/unit/test_email_analyzer.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_email_analyzer.py) | `EmailAnalyzer` | Regex extraction, disposable email detection, Google authentic domain verification (`BUG-ML-002`), typosquatting detection. |
| [`tests/unit/test_preprocessing.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_preprocessing.py) | `cleaner.py` / `dataset.py` | Text normalization, whitespace cleaning, hash generation, grouping. |
| [`tests/unit/test_recommendation.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_recommendation.py) | `RecommendationEngine` | Security incident priority, account takeover password reset, refund routing, fallback rules. |
| [`tests/unit/test_resolution.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_resolution.py) | `ResolutionDetector` | Resolved delivery/refund vs unresolved waiting patterns. |
| [`tests/unit/test_summarizer.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_summarizer.py) | `ConversationSummarizer` | Entity extraction (dates, amounts, order IDs) and structured summary output. |
| [`tests/unit/test_urgency.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_urgency.py) | `UrgencyDetector` | Critical security breaches, urgency adverbs (`urgently`), monetary deduction patterns (`BUG-ML-006`), and anger vs operational risk separation. |
| [`tests/unit/test_url_analyzer.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/unit/test_url_analyzer.py) | `URLAnalyzer` | IP hostnames, punycode homographs, shortener minimum risk (`BUG-ML-007`), and path keyword risks. |

### Integration Tests (`tests/integration/`)
| File | Target Tested | Focus Areas |
|---|---|---|
| [`tests/integration/test_classification_api.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/integration/test_classification_api.py) | `POST /api/v1/classify` | HTTP status codes, schema validation, category and confidence responses. |
| [`tests/integration/test_clustering_api.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/integration/test_clustering_api.py) | `POST /api/v1/cluster*` | Single cluster endpoint, batch cluster endpoint, and cluster metadata list endpoint. |
| [`tests/integration/test_security_api.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/integration/test_security_api.py) | `/api/v1/url/*` & `/email/*` | Security HTTP endpoints, aggregate risk calculation, and quarantine decisions. |
| [`tests/integration/test_summarize_api.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/integration/test_summarize_api.py) | `POST /api/v1/summarize` | Summarization payload validation and entity output. |
| [`tests/integration/test_unified_analyze_api.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/integration/test_unified_analyze_api.py) | `POST /api/v1/analyze` | Master pipeline orchestration combining classification, clustering, urgency, security, and recommendation. |
| [`tests/integration/test_phase5_api.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/integration/test_phase5_api.py) | Operational Endpoints | Health (`/health`), readiness (`/ready`), and capability discovery. |

### Specialized QA & Audit Suites (`tests/qa/`)
| File | Target Tested | Focus Areas |
|---|---|---|
| [`tests/qa/test_qa_security_and_privacy.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/qa/test_qa_security_and_privacy.py) | Security & Privacy (`BUG-ML-001`, `002`) | Recursive PII logging redaction (PANs, JWTs, emails, arbitrary keys) and brand typosquatting checks. |
| [`tests/qa/test_qa_data_pipeline_and_leakage.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/qa/test_qa_data_pipeline_and_leakage.py) | Data Leakage (`BUG-ML-003`) | Strict test asserting 0% complaint text overlap across train, validation, and test splits. |
| [`tests/qa/test_qa_classification_and_abstention.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/qa/test_qa_classification_and_abstention.py) | Classifier & Enums (`BUG-ML-010`) | Abstention threshold validation and canonical enum compliance. |
| [`tests/qa/test_qa_analytics_urgency_recommendation.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/qa/test_qa_analytics_urgency_recommendation.py) | Urgency & Action Rules | Urgency consistency and recommendation engine routing. |
| [`tests/qa/test_qa_intents_and_clustering.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/qa/test_qa_intents_and_clustering.py) | Topics & Stopwords (`BUG-ML-008`) | Topic clustering quality, keyword clarity, and distance stability. |
| [`tests/qa/test_qa_api_and_failures.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/qa/test_qa_api_and_failures.py) | API Resilience | Missing field handling, empty inputs, malformed JSON, and service degradation. |
| [`tests/qa/test_qa_regression_runner.py`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/qa/test_qa_regression_runner.py) | Golden Cases (`BUG-ML-005`) | Runs cases `REG-001` through `REG-020` from `ml_regression_cases.json`, verifying fraud escalation, phishing detection, and OOD handling. |

### Fixtures
| File | Purpose | Description |
|---|---|---|
| [`tests/fixtures/ml_regression_cases.json`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/tests/fixtures/ml_regression_cases.json) | Regression Test Cases | 20 golden complaints (`REG-001` to `REG-020`) specifying expected categories, urgencies, security risks, actions, and resolution statuses. |

---

## 6. Models & Data (`models/` and `data/`)

| File | Purpose | Description |
|---|---|---|
| [`models/complaint_classifier_v1.joblib`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/models/complaint_classifier_v1.joblib) | Serialized Classifier | Serialized TF-IDF + Calibrated LinearSVC pipeline. |
| [`models/clusterer_v1.joblib`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/models/clusterer_v1.joblib) | Serialized Clusterer | Serialized MiniBatchKMeans model. |
| [`models/clusters_metadata.json`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/models/clusters_metadata.json) | Cluster Metadata | Topic names, top keywords, sample complaints, and centroid sizes for all 15 clusters. |
| [`models/classification_metrics.json`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/models/classification_metrics.json) | Classifier Metrics | Accuracy, Macro F1, Weighted F1, and per-class performance records. |
| [`data/processed/train.csv`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/data/processed/train.csv) | Training Set | 20,908 rows generated via leak-free grouped split. |
| [`data/processed/val.csv`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/data/processed/val.csv) | Validation Set | 4,034 rows with zero text overlap with train or test. |
| [`data/processed/test.csv`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/data/processed/test.csv) | Holdout Test Set | 3,997 rows reserved for final leak-free evaluation. |

---

## 7. Audit & Evaluation Reports (`reports/`)

| File | Purpose | Description |
|---|---|---|
| [`reports/ml_test_report.md`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/reports/ml_test_report.md) | Historical Audit Report (Markdown) | The original comprehensive QA/security/reliability audit report that identified defects `BUG-ML-001` through `BUG-ML-010`. Retained unchanged as historical evidence. |
| [`reports/ml_test_report.json`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/reports/ml_test_report.json) | Historical Audit Report (JSON) | Machine-readable audit evidence showing pre-remediation defect states. |
| [`reports/final_model_evaluation.md`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/reports/final_model_evaluation.md) | Final Model Evaluation (Markdown) | Post-remediation evaluation on the leak-free holdout test set with detailed root-cause analysis on dataset limitations. |
| [`reports/final_model_evaluation.json`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/reports/final_model_evaluation.json) | Final Model Evaluation (JSON) | Machine-readable per-class precision, recall, F1, and confusion matrix on the clean test set. |
| [`reports/final_quality_gate.md`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/reports/final_quality_gate.md) | Quality Gate Decision (Markdown) | Summary matrix of all 10 remediated defects, test pass rate (100%), security posture, latency, and production readiness verdict. |
| [`reports/final_quality_gate.json`](file:///Users/muhsilnr/codespace/solwin/app/ml_services/reports/final_quality_gate.json) | Quality Gate Decision (JSON) | Structured report detailing remediation status and quality gate telemetry. |
