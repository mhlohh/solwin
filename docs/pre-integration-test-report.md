# Pre-Integration Test Report

## Executive Summary
This report establishes the baseline status of all independently developed components prior to integration changes.

**Date**: 2026-09-18  
**Integration Status**: BASELINE CAPTURED (Prior to reconciling integration boundaries)

---

## 1. Test Suite Results by Component

| Component | Path | Tool / Framework | Total Tests | Passed | Failed | Skipped | Status | Root Cause of Failure / Issues |
|---|---|---|---|---|---|---|---|---|
| **ML Service (Team A)** | `app/ml_services` | `pytest` / `uv` | 114 | 114 | 0 | 0 | **PASS** | Fully passing. 1 minor Starlette deprecation warning. |
| **Backend (Team B)** | `app/Backend` | `pytest` / `uv` | 151 | 150 | 1 | 0 | **FAIL (1)** | 1 test failed in `tests/test_attachments.py::test_filename_path_traversal_sanitized`. Windows backslash path `..\\..\\boot.ini` produced `____boot.ini` on macOS POSIX Path parsing instead of `boot.ini`. |
| **Data Service (Team C)** | `app/data` | Live API Script (`test_api.py`) | N/A | 0 | 0 | N/A | **STANDALONE** | Script `test_api.py` is an integration test against running server on `:8000`. Does not have isolated unit tests. `clean_data.py` deduplication works. |
| **Frontend (Team D)** | `app/frontend` | None | 0 | 0 | 0 | 0 | **ABSENT** | Only `.gitkeep` present. No frontend implementation code exists in this checkout. |

---

## 2. Static Analysis & Type Checking Baseline

### ML Service (`app/ml_services`)
- `uv run ruff check .` : **PASS** (0 lint violations)
- `uv run mypy src/ scripts/ tests/` : **PASS** (Success: no issues found in 52 source files)

### Backend (`app/Backend`)
- `uv run ruff check .` : **PASS**
- Dependencies: Missing `pyjwt` in `requirements.txt` initially caused `ModuleNotFoundError: No module named 'jwt'` during conftest loading. Installed `pyjwt` in virtual environment.

---

## 3. Discovered Defects Requiring Reconciliation

1. **Path Traversal Sanitizer Cross-Platform Flaw**:
   - `app/Backend/app/services/attachments/validation.py`: `Path(filename).name` on macOS/Linux does not recognize Windows `\\` separators as path delimiters, returning `..\\..\\boot.ini` as a filename, which then gets replaced to `____boot.ini` rather than stripping the parent directory to yield `boot.ini`.
2. **Missing Dependency in Backend**:
   - `pyjwt` was imported by `app/core/auth.py` but omitted from `requirements.txt`.
3. **Backend Database Model vs Canonical Taxonomy**:
   - Backend `ComplaintCategory` enum in `app/models/enums.py` only defines 5 categories (`ACCOUNT_ACCESS`, `PAYMENT_BILLING`, `TECHNICAL_ISSUE`, `SERVICE_REQUEST`, `OTHER`), whereas the canonical taxonomy requires 11 categories (`PAYMENT_TRANSACTION_ISSUE`, `ACCOUNT_LOGIN_PROBLEM`, `PRODUCT_ISSUE`, `DELIVERY_SHIPPING_PROBLEM`, `REFUND_REQUEST`, `SUBSCRIPTION_ISSUE`, `TECHNICAL_PROBLEM`, `SERVICE_QUALITY`, `BILLING_PROBLEM`, `SECURITY_CONCERN`, `OTHER`).
4. **Backend Customer Intelligence LLM Dependency**:
   - `app/Backend/app/services/ai/customer_intelligence.py` relies on live Google Gemini API calls (`google-genai`). When `GEMINI_API_KEY` is not set or in offline mode, it raises HTTP 503. It should consume the ML service endpoint `POST /api/v1/analyze` directly as per architecture specification.
