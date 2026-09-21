# Integration Decisions & Reconciliation Log

This document records the architectural, schema, and operational decisions made during the integration of Team A (ML Service), Team B (Backend), Team C (Data Preprocessing), and Team D (Frontend).

---

## 1. Product Direction & Ingestion Reconciliation
- **Decision:** Terminate all live mailbox integration (IMAP, SMTP, Gmail OAuth, Outlook Graph API, polling queues).
- **Rationale:** Master Integration Mandate Section 1 strictly requires a dataset-driven platform. The Kaggle-derived raw dataset `unified_customer_phishing_data (1).csv` is the canonical source of truth.
- **Action Taken:** Quarantined legacy mailbox polling services. Created batch and streaming dataset runner `scripts/run_inference.py`.

---

## 2. Canonical Business Taxonomy vs. Legacy Backend Enums
- **Decision:** Reconcile `ComplaintCategory` to support all 11 Canonical Business Categories while preserving legacy backend enum identifiers.
- **Rationale:**
  - Section 13 mandates the 11 public business categories (`PAYMENT_TRANSACTION_ISSUE`, `ACCOUNT_LOGIN_PROBLEM`, etc.).
  - Backend had existing internal categories (`ACCOUNT_ACCESS`, `PAYMENT_BILLING`, `ORDER_DELIVERY`, etc.) used in 8 backend unit tests and mock databases.
  - Modifying backend string values broke existing backend test suites.
- **Action Taken:** Updated `app/Backend/app/models/enums.py` to include both canonical categories and legacy aliases. Mapping from ML canonical outputs to backend enum values is seamless, ensuring zero test regressions.

---

## 3. Exclusion of `issue` Column as Predictive Feature
- **Decision:** Strip `issue` from all feature vectors fed into classifiers and embeddings.
- **Rationale:** Detailed audit of `unified_customer_phishing_data (1).csv` confirmed that `issue` is formed by concatenating `{intent} - {message}`, causing near-100% target label leakage.
- **Action Taken:** `issue` is retained in database raw metadata for audit logging only, but never used as an ML feature.

---

## 4. Backend Attachment Security & Path Traversal Fix
- **Decision:** Normalize Windows backslashes (`\`) before POSIX basename extraction in attachment validation.
- **Rationale:** Pre-integration baseline tests failed in `test_attachments.py` on Linux/macOS because `os.path.basename("..\\..\\boot.ini")` does not treat `\` as a path separator on POSIX systems, allowing directory traversal sequences to bypass checks.
- **Action Taken:** Added `.replace('\\', '/')` in `app/Backend/app/services/attachments/validation.py`. All 152 backend tests now pass deterministically.

---

## 5. ML ↔ Backend Boundary & Decoupled Inference
- **Decision:** Backend communicates with ML Service via HTTP REST (`POST /api/v1/analyze`) as the primary architecture, with an approved in-process fallback using `MLServiceOrchestrator` when running offline or embedded.
- **Rationale:** Complies with Section 31 (ML owns inference and model versions; Backend owns persistence, business logic, and API access) while allowing lightweight end-to-end testing in isolated environments.
- **Action Taken:** Added `ML_SERVICE_URL` to `app/Backend/app/core/config.py` and implemented comprehensive end-to-end integration tests in `app/Backend/tests/test_end_to_end_integration.py`.

---

## 6. Social Engineering & Security Intelligence Strategy
- **Decision:** Implement hybrid detection: rule-based signature detection for indicators (urgency, credential harvesting, OTP requests) combined with supervised classification for phishing detection.
- **Rationale:** The raw dataset has an extreme class imbalance (100 phishing cases out of 28,942 records). Supervised models alone suffer from false negatives on zero-day patterns. Rule-based security heuristics guarantee explainability and zero-tolerance escalation.
- **Action Taken:** Evaluated and benchmarked security engine in `app/ml_services/src/ml_service/security/`. Both phishing detection and rule-based social engineering checks are exposed in the canonical ML response.

---

## 7. Logging & PII Redaction Boundary
- **Decision:** Enforce logging redaction at logging boundaries without mutating or truncating raw inference payloads.
- **Rationale:** Machine learning security analysis requires raw indicators (such as original URLs, IPs, and unmasked headers) to detect punycode or homoglyphs. Scrubbing inputs before inference causes security blind spots.
- **Action Taken:** Verification in `test_logging_pii_security` proves that sensitive patterns (credit cards, bearer tokens, passwords) are scrubbed before writing to logs, while ML analysis operates on intact data.
