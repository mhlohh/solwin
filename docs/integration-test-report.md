# End-to-End Integration Test Report

## 1. Scope
This report validates the end-to-end integration lifecycle across all layers:
```
Raw Dataset Record
       ↓
Preprocessing & Safe Normalization
       ↓
ML Orchestrator (`POST /api/v1/analyze`)
       ↓
Canonical ML JSON Payload
       ↓
Backend Persistence Engine
       ↓
Relational Database (Complaints + Intelligence Analysis tables)
       ↓
Backend REST API (`GET /api/v1/complaints/{id}`)
       ↓
Frontend / Client Output
```

## 2. Automated Test Scenario
The integration scenario was automated in `app/Backend/tests/test_end_to_end_integration.py`.

### Test Execution
```bash
cd app/Backend
.venv/bin/pytest tests/test_end_to_end_integration.py -v
```
**Result:**
```
tests/test_end_to_end_integration.py::test_raw_data_to_ml_to_backend_to_api PASSED [ 50%]
tests/test_end_to_end_integration.py::test_dataset_inference_script_execution PASSED [100%]
============================== 2 passed in 0.44s ==============================
```

## 3. Step-by-Step Validation Details

### Step 1: Input Record Ingestion
A representative record from `app/data/unified_customer_phishing_data (1).csv` is supplied:
```json
{
  "complaint_id": "CMP-INT-9999",
  "subject": "Unauthorized debit alert",
  "message": "I was charged $450 unexpectedly on my debit card. Please reverse this transaction immediately.",
  "sender": "victim@example.com"
}
```

### Step 2: ML Analysis Execution
The record is processed by the ML Orchestrator. Output passes validation against the canonical ML schema:
- `complaint_id`: `CMP-INT-9999`
- `classification.category`: `PAYMENT_TRANSACTION_ISSUE`
- `sentiment.label`: `NEGATIVE`
- `urgency.level`: `HIGH`
- `security.risk_level`: `SAFE`
- `overall_risk.level`: `HIGH`
- `recommendation.primary_action`: `PAYMENT_TEAM_REVIEW`
- `processing_time_ms`: `< 2.0 ms`

### Step 3: Backend Persistence
Backend stores the complaint and analysis into the relational database:
- `complaints` table: stores raw metadata, sender, subject, message, and complaint status.
- `complaint_analyses` table: stores category, sentiment, urgency, security risk, overall risk, recommendation, and model version metadata.
- Transaction commits cleanly without constraint violations.

### Step 4: Backend API Retrieval
The complaint is retrieved via the Backend REST API (`GET /api/v1/complaints/CMP-INT-9999`):
- HTTP Status: `200 OK`
- `complaint_id`: Matches `CMP-INT-9999`
- Category: Preserved as `PAYMENT_TRANSACTION_ISSUE`
- Full intelligence details accessible to dashboard clients.

## 4. Batch Dataset Ingestion Validation
The batch runner `app/ml_services/scripts/run_inference.py` was executed against the actual Kaggle dataset:
```bash
cd app/ml_services
.venv/bin/python scripts/run_inference.py --input ../data/unified_customer_phishing_data\ \(1\).csv --limit 50
```
**Results:**
- Processed: 50 records
- Failed: 0
- Phishing Detections: 0 (benign records)
- Average Processing Time: 1.35 ms / record
- Output saved to `reports/inference_results.json`
