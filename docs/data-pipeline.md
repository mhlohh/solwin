# Data Pipeline Specification

## 1. Overview
The platform is strictly **dataset-driven**. The primary source of truth is the Kaggle-derived raw dataset:
`app/data/unified_customer_phishing_data (1).csv`

Raw data is treated as **immutable**. It is never overwritten or mutated in-place.

## 2. Directory Structure & Lifecycle
The repository organizes data according to pipeline stages:

- `app/data/`: Location of immutable raw dataset `unified_customer_phishing_data (1).csv`.
- `app/data/backend/clean_data.py`: Data cleaning and preprocessing module owned by Team C.
- `app/data/interim/`: Normalized and validated intermediate datasets.
- `app/data/processed/`: Deduplicated and grouped train/val/test splits (`train.csv`, `val.csv`, `test.csv`).
- `app/ml_services/reports/`: Data quality reports, leakage audit results, and quality gate evaluations.
- `app/ml_services/scripts/run_inference.py`: Production dataset ingestion and inference runner.

## 3. Raw Dataset Profile
- **Total Records:** 28,942 rows
- **Columns (11):** `id`, `domain`, `channel`, `message`, `subject`, `intent`, `issue`, `technique`, `phishing`, `sender`, `label`
- **Missing Values:**
  - `subject`: 100 missing rows (handled gracefully by falling back to `message` alone without fabricating text).
  - `technique`: 28,842 missing (only populated for the 100 phishing cases).
  - `domain`: 100 missing.
  - `channel`: 100 missing.
  - `sender`: 100 missing.
- **Phishing Distribution:**
  - 100 phishing records (0.35%)
  - 28,842 benign customer support records (99.65%)

## 4. Leakage Control & Target Protection
### The `issue` Field
Investigation of the raw data revealed that the `issue` column directly concatenates `{intent} - {message}`:
- **Decision:** The `issue` column is strictly **excluded** from all model training features to prevent catastrophic target leakage.
- Input text for classification and NLP models is strictly:
  $$\text{input\_text} = \text{subject} + \text{" "} + \text{message} \quad (\text{or } \text{message alone if subject is null})$$

### Deduplication & Split Leakage Prevention
- Simple row-level random splitting causes data leakage because near-identical or exact-duplicate complaint texts cross split boundaries.
- **Grouped Splitting:** Cleaned complaint texts are normalized (lowercased, punctuation-stripped, whitespace-collapsed) and grouped. All identical texts are assigned to the same partition.
- **Validation Invariant:**
  $$\text{Train} \cap \text{Val} = \emptyset, \quad \text{Train} \cap \text{Test} = \emptyset, \quad \text{Val} \cap \text{Test} = \emptyset$$

## 5. Canonical Category Mapping
The raw dataset contains 65 fine-grained intent classes. The platform deterministically maps these into the **11 Canonical Public Business Categories**:
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

The deterministic mapping table is version-controlled in `app/ml_services/src/ml_service/preprocessing/taxonomy.py`.

## 6. Training vs. Inference Preprocessing
- **Training Pipeline:** Strips stopwords, normalizes case, removes formatting artifacts, balances sample weights, performs grouped splitting, and encodes labels.
- **Inference Pipeline (`Safe Normalization`):**
  - Normalizes text for TF-IDF / embeddings.
  - **CRITICAL:** Preserves security-critical tokens, including raw URLs, IP addresses, email addresses, credential keywords ("password", "OTP", "login"), and casing where indicators are sensitive.

## 7. Execution & Reproducibility
To run data cleaning:
```bash
python3 app/data/backend/clean_data.py
```
To run end-to-end dataset inference:
```bash
cd app/ml_services
.venv/bin/python scripts/run_inference.py --input ../data/unified_customer_phishing_data\ \(1\).csv --limit 500
```
