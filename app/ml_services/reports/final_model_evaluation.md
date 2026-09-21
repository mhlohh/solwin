# Final Model Evaluation Report

## 1. Overview and Dataset Versioning

- **Evaluation Date**: 2026-09-18
- **Dataset Version**: `2.0.0-leak-free`
- **Split Methodology**: Deterministic normalized text hashing (`src/ml_service/preprocessing/dataset.py`)
- **Total Samples**:
  - Train: 20,908 rows
  - Validation: 4,034 rows
  - Test: 3,997 rows
- **Unique Complaint Texts**: 17,515
- **Cross-Split Data Leakage**:
  - Train ∩ Validation Overlap: **0 records (0.00%)**
  - Train ∩ Test Overlap: **0 records (0.00%)**
  - Validation ∩ Test Overlap: **0 records (0.00%)**

---

## 2. Model Architecture

- **Classifier**: `models/complaint_classifier_v1.joblib`
- **Feature Pipeline**:
  - Word n-grams: (1, 2)
  - Character n-grams (within word boundaries): (3, 5)
  - Max features: 25,000
  - Sublinear term frequency scaling (`sublinear_tf=True`)
- **Estimator**: `CalibratedClassifierCV(estimator=LinearSVC(class_weight="balanced", dual="auto"), method="sigmoid", cv=3)`

---

## 3. Comprehensive Performance Metrics (Leak-Free Test Set)

| Metric | Pre-Remediation (Audit Contaminated Test) | Post-Remediation (Clean Leak-Free Test) | Delta |
|---|---|---|---|
| **Accuracy** | 16.59% | **19.44%** | +2.85% |
| **Macro F1** | 0.1065 | **0.1144** | +0.0079 |
| **Weighted F1** | 0.2099 | **0.2355** | +0.0256 |
| **Macro Precision** | 0.1332 | **0.1304** | -0.0028 |
| **Macro Recall** | 0.1389 | **0.1484** | +0.0095 |

---

## 4. Per-Class Metrics

| Category | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| `DELIVERY_SHIPPING_PROBLEM` | 0.5680 | 0.2168 | 0.3138 | 1,831 |
| `PRODUCT_ISSUE` | 0.2212 | 0.1769 | 0.1966 | 684 |
| `REFUND_REQUEST` | 0.2519 | 0.1733 | 0.2054 | 750 |
| `SECURITY_CONCERN` | 0.1205 | 0.2022 | 0.1510 | 183 |
| `SERVICE_QUALITY` | 0.0795 | 0.1582 | 0.1058 | 196 |
| `OTHER` | 0.1049 | 0.2353 | 0.1451 | 119 |
| `PAYMENT_TRANSACTION_ISSUE` | 0.0514 | 0.1374 | 0.0748 | 131 |
| `BILLING_PROBLEM` | 0.0213 | 0.2281 | 0.0390 | 57 |
| `SUBSCRIPTION_ISSUE` | 0.0092 | 0.0667 | 0.0161 | 15 |
| `ACCOUNT_LOGIN_PROBLEM` | 0.0065 | 0.0370 | 0.0111 | 27 |
| `TECHNICAL_PROBLEM` | 0.0000 | 0.0000 | 0.0000 | 4 |

---

## 5. Root Cause Analysis & Quality Gate Reality

1. **Severe Label Ambiguity & Conversational Noise**:
   Over 45% of customer messages in the original raw dataset consist of brief positive ratings or pleasantries (`"Good"`, `"Nice"`, `"Thank you"`, `"Great service"`, `"Ok"`). These short phrases were assigned to different business categories in the raw data, preventing any linear classifier or transformer from learning clean class boundaries.
2. **Extreme Imbalance in Ground Truth**:
   The minority categories such as `TECHNICAL_PROBLEM` (4 test samples) and `SUBSCRIPTION_ISSUE` (15 test samples) lack sufficient distinct examples for statistical generalizability.
3. **Quality Gate Requirement (Macro F1 >= 0.75)**:
   In accordance with the audit guidelines, **Macro F1 >= 0.75 is NOT falsely claimed**. With the present raw data distribution, achieving 0.75 Macro F1 is mathematically unachievable without:
   - Filtering out generic non-complaint conversational feedback from complaint classification.
   - Collecting 2,000+ balanced, accurately labeled examples for `TECHNICAL_PROBLEM`, `ACCOUNT_LOGIN_PROBLEM`, and `SUBSCRIPTION_ISSUE`.
   - Applying human-in-the-loop abstention thresholds with fallback routing to human agents.
