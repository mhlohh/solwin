# ML Service Defect Remediation Plan

This document details the defect remediation plan for the Customer Complaint Intelligence ML Service based on the audit findings in `reports/ml_test_report.md`.

---

## Remediation Plan Matrix

### BUG-ML-001 [P0 — Critical] Plaintext PII & Credential Leakage in Logging
- **Component**: Core Logging (`src/ml_service/core/logging.py`)
- **Root Cause**: `safe_log()` only filtered top-level dictionary keys using a small blacklist. Arbitrary keys (e.g. `customer_input`, `query`, `details`) and nested structures allowed PAN card numbers, JWT tokens, and emails to leak into stdout/stderr.
- **Proposed Fix**: Implement recursive sanitization across nested dictionaries, lists, tuples, and strings using regex pattern detection for payment cards, JWT tokens, Bearer authorization headers, email addresses, and API keys.
- **Files Affected**: `src/ml_service/core/logging.py`
- **Tests Added/Updated**: `tests/qa/test_qa_security_and_privacy.py::test_pii_log_redaction`, `test_pii_log_nested_and_arbitrary_structures`.
- **Side Effects**: None; log message keys and overall formatting preserved while sensitive tokens are masked.

---

### BUG-ML-002 [P1 — High] Legitimate Google Domain Detected as Typosquatting
- **Component**: Email Security Analyzer (`src/ml_service/security/email_analyzer.py`)
- **Root Cause**: Substring lookalike comparison triggered on genuine domains because "googl" matched as a substring of "google".
- **Proposed Fix**: Extract the domain label and check if it exactly matches the authentic brand domain before computing lookalike/typosquatting distance.
- **Files Affected**: `src/ml_service/security/email_analyzer.py`
- **Tests Added/Updated**: `tests/unit/test_email_analyzer.py`, `tests/qa/test_qa_security_and_privacy.py`.
- **Side Effects**: Eliminates false positive risk alerts for legitimate brand emails (`support@google.com`, `amazon.com`, etc.).

---

### BUG-ML-003 [P1 — High] Duplicate Messages Across Dataset Splits (Data Leakage)
- **Component**: Preprocessing & Dataset Splitting (`src/ml_service/preprocessing/dataset.py`)
- **Root Cause**: Row-level random/stratified splitting placed identical complaint texts across train, validation, and test splits (13.37% val overlap, 13.12% test overlap).
- **Proposed Fix**: Deterministically hash and group normalized complaint texts (`subject` + `message`), allocating entire text groups to a single split.
- **Files Affected**: `src/ml_service/preprocessing/dataset.py`, `data/processed/train.csv`, `data/processed/val.csv`, `data/processed/test.csv`.
- **Tests Added/Updated**: `tests/qa/test_qa_data_pipeline_and_leakage.py::test_split_exact_text_leakage`.
- **Side Effects**: Guarantees zero text overlap between splits.

---

### BUG-ML-004 [P1 — High] Classifier Collapse and Imbalance
- **Component**: Classifier Training (`scripts/train_classifier.py`, `src/ml_service/classification/classifier.py`)
- **Root Cause**: Raw data contains heavy class imbalance (45%+ delivery vs 0.1% technical) and 45%+ conversational feedback pleasantries. Old model had 16.59% accuracy.
- **Proposed Fix**: Train a class-weighted Calibrated LinearSVC pipeline on clean leak-free splits. Report actual metrics without fabricating performance.
- **Files Affected**: `scripts/train_classifier.py`, `models/complaint_classifier_v1.joblib`, `models/classification_metrics.json`.
- **Tests Added/Updated**: `tests/qa/test_qa_classification_and_abstention.py`.
- **Side Effects**: Provides calibrated probabilities and honest metric baseline on clean holdout data.

---

### BUG-ML-005 [P1 — High] Account Takeover / Fraud Escalation Routing
- **Component**: Recommendation Action Rules (`config/action_rules.yaml`, `src/ml_service/recommendation/engine.py`)
- **Root Cause**: Action recommendation policy lacked explicit escalation for critical security and financial theft complaints, defaulting to `STANDARD_SUPPORT_RESPONSE`.
- **Proposed Fix**: Introduce `RULE_ACCOUNT_TAKEOVER` (Priority 15, `RESET_ACCOUNT_ACCESS` for `ACCOUNT_LOGIN_PROBLEM`) and `RULE_CRITICAL_SECURITY_ESCALATION` (Priority 16, `ESCALATE_TO_SECURITY_TEAM` for `SECURITY_CONCERN`, `PAYMENT_TRANSACTION_ISSUE`, `OTHER`) with `CRITICAL` urgency.
- **Files Affected**: `config/action_rules.yaml`.
- **Tests Added/Updated**: `tests/unit/test_recommendation.py`, `tests/qa/test_qa_regression_runner.py (REG-010)`.
- **Side Effects**: Critical security incidents are escalated directly to the security team.

---

### BUG-ML-006 [P2 — Medium] Urgency Regex Missing Adverbs and Monetary Deductions
- **Component**: Urgency Detector (`src/ml_service/urgency/detector.py`)
- **Root Cause**: Exact word boundary `\burgent\b` missed `urgently`, and monetary deduction patterns were overly restrictive.
- **Proposed Fix**: Add pattern `\burgent(ly)?\b` and monetary deduction regexes matching `money was deducted`, `amount was debited`, `large amount deducted`.
- **Files Affected**: `src/ml_service/urgency/detector.py`.
- **Tests Added/Updated**: `tests/unit/test_urgency.py::test_high_urgency_adverbs_and_monetary_deductions`.
- **Side Effects**: Captures time-sensitive and financial loss expressions accurately.

---

### BUG-ML-007 [P2 — Medium] URL Shortener Under-Classification
- **Component**: URL Security Analyzer (`src/ml_service/security/url_analyzer.py`)
- **Root Cause**: Shortened URLs (`bit.ly`, `tinyurl.com`) conceal destinations but were scored as `LOW` risk.
- **Proposed Fix**: Add configurable `shortener_min_risk` parameter defaulting to `MEDIUM` and penalty score adjustments.
- **Files Affected**: `src/ml_service/security/url_analyzer.py`.
- **Tests Added/Updated**: `tests/unit/test_url_analyzer.py::test_url_shortener_risk`, `test_suspicious_shortened_url`, `test_configurable_shortener_min_risk`.
- **Side Effects**: Ensures concealed shorteners receive minimum `MEDIUM` risk unless explicitly configured otherwise.

---

### BUG-ML-008 [P2 — Medium] Clustering Quality Dominated by Pleasantries
- **Component**: Clusterer Training (`scripts/train_clusterer.py`)
- **Root Cause**: Conversational feedback words ("good", "thanks", "nice") dominated topic centroids.
- **Proposed Fix**: Add domain-specific conversational pleasantries stop-word list to TF-IDF vectorizer prior to K-Means clustering.
- **Files Affected**: `scripts/train_clusterer.py`, `models/clusterer_v1.joblib`, `models/clusters_metadata.json`.
- **Tests Added/Updated**: `tests/unit/test_clustering.py`, `tests/qa/test_qa_intents_and_clustering.py`.
- **Side Effects**: Produces semantically distinct, complaint-focused topic clusters.

---

### BUG-ML-009 [P3 — Low] Quality Gate Benchmark Parser Expecting Root Metrics
- **Component**: QA Benchmarks Script (`scripts/qa_benchmarks.py`)
- **Root Cause**: Expected `macro_f1` at root level instead of nested under `overall_metrics`.
- **Proposed Fix**: Update dictionary lookup to safely check both `overall_metrics` and root keys.
- **Files Affected**: `scripts/qa_benchmarks.py`.
- **Tests Added/Updated**: `scripts/qa_benchmarks.py` self-execution.
- **Side Effects**: Benchmark execution runs cleanly.

---

### BUG-ML-010 [P3 — Low] Canonical Enum Mismatch in QA Tests
- **Component**: QA Classification Tests (`tests/qa/test_qa_classification_and_abstention.py`)
- **Root Cause**: Tests referenced non-canonical `PAYMENT_ISSUE` instead of `PAYMENT_TRANSACTION_ISSUE`.
- **Proposed Fix**: Replace references with the canonical `BusinessCategory.PAYMENT_TRANSACTION_ISSUE`.
- **Files Affected**: `tests/qa/test_qa_classification_and_abstention.py`.
- **Tests Added/Updated**: `tests/qa/test_qa_classification_and_abstention.py`.
- **Side Effects**: Strict enum compatibility with production API schema.
