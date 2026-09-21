# Solwin — Hackathon Scoring Guide

**Map of the 11 scoring criteria → exactly how Solwin implements each one, where the code lives, and how to demo it.**

System under discussion (all paths relative to repo root):

| Layer | Path | Tech | Port |
|---|---|---|---|
| Data preprocessing | `app/data/backend/` | pandas, dependency-free canonical cleaning | — |
| ML service | `app/ml_services/` | FastAPI, scikit-learn (joblib), Gemini LLM | 8000 |
| Backend API | `app/Backend/` | FastAPI, SQLAlchemy 2, SQLite/PostgreSQL, Alembic | 8001 |
| Frontend | `app/frontend/` | React 19 + Vite + Tailwind + Recharts | 5173 |

**Validation status:** 130 ML-service tests + 107 backend tests pass; frontend `tsc + vite` build clean. Full-stack live check performed end to end (data → ML → backend → Gemini → DB → UI).

---

## Criterion 1 — Problem Understanding & Approach (10 pts)

**Judges look for:** clarity of problem understanding; soundness and relevance of the approach.

**The problem Solwin solves:** support teams receive customer messages through many channels. Some messages are ordinary complaints; some are phishing/social-engineering attacks that *arrive through the support channel itself* and target agents or customers. Today these two concerns are handled by separate tools (a helpdesk and a spam filter) that don't talk to each other.

**The approach — one pipeline, two lenses:**

1. Every inbound message is processed once by a single canonical pipeline.
2. It produces **customer intelligence** (what does the customer need?) and **security intelligence** (is this message an attack?) simultaneously.
3. A deterministic **fusion layer** combines both into one calibrated recommended action — e.g. a critical-security message is escalated to the security team even if the customer request inside it is urgent.

**Why this is sound (say this to judges):**
- One inference pass, two value streams — cheap to run, no duplicated models.
- The fusion step is *deterministic and explainable* (see C8), not another black box.
- The canonical output schema (`CustomerReviewOutput`, 15 sections) is enforced at the ML boundary **and re-validated before persistence**, so the database can never hold a payload that doesn't match the contract.

**Where the code lives:**
- Fusion logic: `app/Backend/app/services/unified_intelligence.py` → `determine_final_action()`
- Canonical contract: `app/ml_services/src/ml_service/api/schemas.py` (ML side) and `app/Backend/app/schemas/review.py` (backend side)

**Demo:** draw the 4-layer diagram (data → ML :8000 → backend :8001 → UI :5173) on a whiteboard, then show `POST /api/v1/analyze` returning both lenses in one JSON.

---

## Criterion 2 — Dataset & Preprocessing (5 pts)

**Judges look for:** suitable dataset chosen/created; cleaning, tokenization, basic NLP preprocessing shown.

**Dataset:** a unified customer-support + phishing corpus (`app/data/unified_customer_phishing_data.csv`) combining real complaint text with labeled phishing/legitimate examples. Fields preserved end-to-end: `id, domain, channel, message, subject, intent, issue, technique, phishing, sender, label`.

**Preprocessing pipeline (single source of truth):** `app/data/backend/clean_data.py`
- `normalize_text()` — Unicode NFKC normalization, **strips control characters** (null bytes, backspace — hardened so untrusted content can't carry them downstream), whitespace collapse.
- `clean_csv_data()` — fills nulls, deduplicates rows, preserves all source identifier columns.
- **Leakage safety:** `build_complaint_text()` combines subject+message but **deliberately excludes the `issue` column** — `issue` is a model *target*, not a feature, so classification can't cheat by reading it. This is a judges' favorite detail.
- The ML service and the backend **import this exact module** rather than keeping their own copies (the backend previously had a stale inline copy; that bug was found and fixed — a good QA story).

**Where NLP preprocessing shows in the ML service:** `app/ml_services/src/ml_service/preprocessing/`
- `cleaner.py` — imports the canonical data-layer cleaning, adds ML-specific normalization.
- `dataset.py` — reproducible train/test splits, stratification, deterministic seeds.

**Study note — "tokenization" question:** text vectorization for the classical models is inside the trained scikit-learn pipelines (TF-IDF + classifier persisted together as one joblib artifact, so train/serve skew is impossible). The LLM path (Gemini) is tokenized by the model provider. If asked where "tokenization" happens: *TF-IDF word n-gram vectorization inside the persisted sklearn pipelines; NFKC normalization + control-char stripping before it; provider-side tokenization for the LLM.*

**Demo:** `python -c` snippet importing `normalize_text("Hello \x00\x08  world  ")` → `"Hello world"` — live proof of control-char stripping and whitespace collapse.

---

## Criterion 3 — Complaint Classification (10 pts)

**Judges look for:** automatic classification into at least 4–5 meaningful categories.

**Solwin classifies into 11 business categories** (more than double the requirement):

`PAYMENT_TRANSACTION_ISSUE · ACCOUNT_LOGIN_PROBLEM · PRODUCT_ISSUE · DELIVERY_SHIPPING_PROBLEM · REFUND_REQUEST · SUBSCRIPTION_ISSUE · TECHNICAL_PROBLEM · SERVICE_QUALITY · BILLING_PROBLEM · SECURITY_CONCERN · OTHER`

**How:**
- ML: `app/ml_services/src/ml_service/classification/classifier.py` — a trained scikit-learn classifier (persisted as `models/complaint_classifier_v1.joblib`) with **calibrated probabilities** and an abstention mechanism: below the confidence threshold (`model_confidence_threshold = 0.60`) it marks `needs_review` instead of guessing — see the `confidence` + `needs_review` fields in every classification result.
- A separate **fine-grained intent classifier** (`models/intention_classifier_v1.joblib`, `intent_classifier_v1.joblib`) maps each complaint to a specific intent (e.g. "Credential Harvesting", "Seller Cancelled Order") via `intent_category_mapping.yaml`.
- Backend mirror enum: `app/Backend/app/models/enums.py` → `ComplaintCategory`.
- Gemini augmentation: when `GEMINI_ENABLED=true`, the LLM can refine classification (`gemini_use_for_classification`).

**Demo:** live curl to `:8000/api/v1/analyze/review` with a billing complaint → `classification.category = REFUND_REQUEST`, `confidence 0.18, needs_review true` (abstention visible!), and a phishing message → `SECURITY_CONCERN / Credential Harvesting`. Show both in one minute.

---

## Criterion 4 — Sentiment Analysis (10 pts)

**Judges look for:** accurate Positive/Neutral/Negative; **bonus for emotion/urgency detection** — Solwin does both bonuses.

**Sentiment:**
- ML: `app/ml_services/src/ml_service/sentiment/analyzer.py` (`models/` persisted model) returns label + continuous score. Gemini can augment (`gemini_use_for_sentiment`).
- Backend: `app/Backend/app/services/ai/customer_intelligence.py` — Gemini returns structured output (`response_schema=CustomerIntelligenceOutput`) including **both** sentiment and a specific **emotion** ("Frustration", "Anxiety", "Satisfaction").

**Urgency (the bonus):** `app/ml_services/src/ml_service/urgency/detector.py` — `UrgencyDetector` produces `urgency.level` + `urgency.score` + `urgency.reasons` (explainable!). Live example: `urgency HIGH (0.85)` on the phishing demo message.

**Demo:** one conversation analyzed by Gemini shows `sentiment: NEGATIVE, emotion: Frustration, priority: HIGH`; the ML review endpoint shows `urgency HIGH 0.85` with the reasons array printed.

---

## Criterion 5 — Keyword Extraction & Summarization (10 pts)

**Judges look for:** identification of frequently reported issues + concise conversation summarization.

**Two distinct features:**

1. **Summarization + key phrases:** `app/ml_services/src/ml_service/summarization/summarizer.py` → `summarize()` returns a concise summary plus `key_phrases` (extracted in `summarizer.py:154` `_extract_key_phrases`); Gemini can produce the summary when enabled. The canonical schema exposes `summary.text` and `keywords`.
2. **Frequently reported issues (aggregated):** `app/ml_services/src/ml_service/analytics/frequency.py` — builds frequency counts over persisted analyses; the backend surfaces this as `GET /api/v1/analytics/customer/top-issues` returning `{issue, count}` ranked pairs, and the Dashboard/Insights UI renders them as bars.

**Demo:** show `keywords: ["refund"]` + `summary.text` in the ML response, then open the dashboard's "Most reported issues" panel fed by `top-issues`.

---

## Criterion 6 — Phishing / URL & Email Detection (15 pts — the biggest one)

**Judges look for:** extraction & analysis of suspicious URLs, domains, email addresses (lookalike, mismatch, etc.).

**This is Solwin's strongest section — three dedicated analyzers:**

1. **URL analyzer** — `app/ml_services/src/ml_service/security/url_analyzer.py` (`analyze_url`, `analyze_text`): extracts every URL and checks: URL shorteners, IP-literal hosts, **lookalike/typosquatted domains** (e.g. `se1win-billing.com` vs `solwin`), suspicious TLDs (`.tk`, `.ru`…), credential-path patterns (`/login`, `/verify`), subdomain-vs-host mismatch. Full analysis with per-URL signals is in the canonical `security.urls` array.
2. **Email analyzer** — `app/ml_services/src/ml_service/security/email_analyzer.py` (`analyze_email`, `analyze_text`): extracts email addresses and checks display-name spoofing, **domain mismatch** (sender claims to be support@ but writes from another domain), lookalike domains, free-mail impersonation of corporate support.
3. **Phishing detector (fusion of 1+2+7):** `app/Backend/app/services/security/phishing_detector.py` — combines URL results, email results, and social-engineering signals into `threat_detected`, `threat_type ∈ {PHISHING, SUSPICIOUS_MESSAGE, NONE}`, and human-readable indicators.

**Live proof (already demonstrated this thread):** a message containing `support@se1win-billing.com` + `http://solwin-verify.tk/login` produced:
`phishing.detected = true (0.90 confidence)`, 1 URL flagged, 1 email flagged, security risk `HIGH (0.95)`, overall risk `CRITICAL`.

**Demo script (memorize this):** paste the lookalike-domain message into the Threats/analyzer → point at the flagged URL with its signals → point at the flagged email → read the phishing confidence. Then show the same flags persisted in the Threats UI directory.

---

## Criterion 7 — Social Engineering Detection (10 pts)

**Judges look for:** detection of at least 3–4 techniques. **Solwin detects 4 canonical techniques** (plus combinations):

`URGENCY · CREDENTIAL_HARVESTING · OTP_REQUEST · IMPERSONATION`

**Two independent engines:**
- ML service: `app/ml_services/src/ml_service/security/` + Gemini social-engineering refinement (`gemini_use_for_social_engineering`) → canonical `security.social_engineering.techniques`.
- Backend (deterministic, explainable): `app/Backend/app/services/security/social_engineering.py` — pattern-based detector with per-technique lexicons; results feed the `RiskEngine`.

**Live proof:** demo text "reset your password immediately at http://secure-solwin.tk/verify … Reply with your OTP code 4455" → `techniques: ['URGENCY', 'OTP_REQUEST']`, `threat_type: PHISHING`, risk `CRITICAL`.

**Demo:** fire that exact message, then show the techniques list persisted in the threat record and rendered as chips in the UI.

---

## Criterion 8 — Risk Classification (5 pts)

**Judges look for:** clear Low/Medium/High/Critical combining **customer + security** intelligence.

**Two-layer answer:**

1. **Security risk engine (deterministic, explainable scoring):** `app/Backend/app/services/security/risk_engine.py`
   - Weights: credential harvesting +30, OTP request +30, suspicious URL +25 each (cap 50), suspicious email +20, impersonation +15, urgency +10.
   - Bands: `≥70 (or phishing + ≥50) → CRITICAL`, `≥40 HIGH`, `≥16 MEDIUM`, else LOW — each band with a concrete recommended action.
   - Every point of the score is traceable to a named reason in `risk_reasons` — judges can audit it.
2. **Fusion with customer intelligence:** `unified_intelligence.py → determine_final_action()` merges security risk × customer priority into the final recommendation (e.g. critical security beats urgent customer request; high customer priority with no threat → expedite support).

**Demo:** show the same message scoring MEDIUM with only urgency, then CRITICAL once a suspicious URL is added — the weighting is live-auditable.

---

## Criterion 9 — Dashboard & Visualization (10 pts)

**Judges look for:** interactive dashboard showing **customer KPIs and security insights together**.

**Solwin's UI (redesigned as a practical operator console):**
- **Dashboard** (`app/frontend/src/pages/Dashboard.tsx`): conversation KPIs (total/open/unresolved/urgent), threats detected + critical, latest conversations with status chips, recent threats with risk badges, sentiment bars, top issue categories — customer and security side by side.
- **Threats directory** (`Threats.tsx`): filterable table of every persisted threat record (classification, risk, social engineering, tactics, time) + detail view with flagged URLs/emails.
- **Customer insights** (`CustomerInsights.tsx`): volume trend (14d), category distribution, priority mix, sentiment mix, most-reported issues.
- **Security analytics** (`SecurityAnalytics.tsx`): threat velocity, risk distribution, threat-type breakdown, social-engineering technique frequency, recent critical threats.
- **Conversation detail**: transcript + AI triage + security scan + "Run AI analysis" button that triggers **live Gemini** through the full stack.

**Interactivity is real:** search, status/channel filters, risk-level filter, pagination, theme toggle, and the analysis button all hit the live API. Charts are Recharts (tooltips, legends); no mock data anywhere — the mock layer was deleted and services fail with explicit error messages.

**Demo:** dashboard → click a conversation → Run AI analysis (live Gemini ~2–3 s) → open Threats → filter MEDIUM → open detail. Under 2 minutes.

---

## Criterion 10 — Innovation & Technical Depth (5 pts)

**Judges look for:** originality, technical sophistication, effective use of NLP/ML/LLM.

**The strongest talking points:**
1. **Hybrid classical-ML + LLM architecture with graceful degradation** — scikit-learn models do the heavy lifting offline (no API cost/latency); Gemini augments specific fields and is *optional at startup*. If the API key is missing or Google is down, every stage fails soft with warnings. Retry with exponential backoff (4 attempts) handles transient 503s.
2. **Contract-first canonical schema** (`CustomerReviewOutput`, 15 sections) validated at the ML boundary and **re-validated before persistence** — a distributed-systems discipline judges rarely see in hackathons.
3. **Deterministic, auditable risk scoring** — no black-box risk; every point traceable to a named signal.
4. **Leakage-safe preprocessing** (the `issue`-exclusion story) + control-char stripping.
5. **Calibrated abstention** — the classifier says "needs_review" instead of guessing below threshold.
6. **Clustering** (`models/clusterer_v1.joblib`) groups complaints into named clusters ("Delivery Shipping Problem: satisfied, refund") — unsupervised layer on top of classification.
7. **Engineering quality:** 237 automated tests across services, Alembic migrations, portable SQL (PG-native UUID/JSONB with SQLite fallback), three-service test suites all green.

---

## Criterion 11 — Presentation, Clarity & Q&A (10 pts)

**Judges look for:** clear 15–20 min presentation in English; ability to answer questions.

**Suggested 18-minute structure:**

| Min | Section | What you show |
|---|---|---|
| 0–2 | Problem | Support channels are an attack surface; two tools today, zero fusion |
| 2–4 | Architecture | 4-layer diagram; single canonical schema across services |
| 4–7 | Data & preprocessing | Dataset fields, leakage-safety, control-char stripping (C2) |
| 7–10 | ML engine live | curl `analyze/review`: 11 categories, urgency, keywords, summary, cluster (C3–C5) |
| 10–14 | **Security deep-dive** | Lookalike-domain phishing message → URL+email flagged, techniques, CRITICAL (C6–C8) — your 15-pointer, spend time here |
| 14–16 | Dashboard tour | Customer KPIs + security insights together; live Gemini button (C9) |
| 16–18 | Engineering depth | Contract validation, hybrid LLM strategy, 237 tests (C10) |

**Q&A preparation — likely questions and answers:**
- *"Where is tokenization?"* → TF-IDF n-gram vectorization inside the persisted sklearn pipelines; NFKC+control-char cleaning before; provider-side tokenization for Gemini.
- *"What if Gemini is down?"* → every LLM stage is optional with local fallback; failures degrade to warnings, never 500s; retries with backoff for transient 503s.
- *"How do you avoid data leakage?"* → the `issue` column is a target; `build_complaint_text()` excludes it from features.
- *"Why not one big LLM prompt for everything?"* → cost, latency, determinism. Classical models give reproducible calibrated probabilities; the LLM is used where language nuance pays (emotion, summary); risk fusion is deterministic so it's auditable.
- *"How is risk computed?"* → walk the weight table (C8) — every point maps to a reason string.
- *"Is the DB schema production-ready?"* → PostgreSQL with native UUID/JSONB + Alembic migrations; SQLite fallback for local dev via SQLAlchemy variants.

---

## Quick reference — file map for judges' deep-dive

| Criterion | Primary files |
|---|---|
| C1 Fusion | `app/Backend/app/services/unified_intelligence.py` |
| C2 Data | `app/data/backend/clean_data.py`, `app/ml_services/src/ml_service/preprocessing/` |
| C3 Classification | `app/ml_services/src/ml_service/classification/classifier.py`, `app/Backend/app/models/enums.py` |
| C4 Sentiment/Urgency | `app/ml_services/src/ml_service/sentiment/analyzer.py`, `app/ml_services/src/ml_service/urgency/detector.py`, `app/Backend/app/services/ai/customer_intelligence.py` |
| C5 Keywords/Summary | `app/ml_services/src/ml_service/summarization/summarizer.py`, `app/ml_services/src/ml_service/analytics/frequency.py` |
| C6 Phishing | `app/ml_services/src/ml_service/security/url_analyzer.py`, `.../email_analyzer.py`, `app/Backend/app/services/security/phishing_detector.py` |
| C7 Social eng. | `app/Backend/app/services/security/social_engineering.py` |
| C8 Risk | `app/Backend/app/services/security/risk_engine.py` |
| C9 Dashboard | `app/frontend/src/pages/*` |
| C10 Depth | `app/ml_services/src/ml_service/api/schemas.py`, `app/Backend/app/services/ml_service_client.py`, test suites |
