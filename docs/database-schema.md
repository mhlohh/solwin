# Database Schema Documentation

## 1. Overview
The database backend is built with **PostgreSQL 16** and **SQLAlchemy 2.0**. All schema definitions support strict typing, foreign key constraints with cascade rules, and automated indexing on query-heavy columns.

---

## 2. Core Relational Tables

### 2.1 `conversations`
Tracks the lifecycle of each customer inquiry thread.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Globally unique identifier |
| `conversation_reference` | `VARCHAR(64)` | `UNIQUE, INDEX, NOT NULL` | Stable human-readable reference (`CONV-000001`) |
| `customer_name` | `VARCHAR(255)` | `NULLABLE` | Name of customer |
| `customer_email` | `VARCHAR(255)` | `INDEX, NULLABLE` | Email of customer |
| `channel` | `ENUM` | `NOT NULL, DEFAULT 'CHAT'` | `EMAIL`, `CHAT`, `TICKET`, `SOCIAL_MEDIA`, `OTHER` |
| `subject` | `VARCHAR(255)` | `NULLABLE` | Conversation subject |
| `status` | `ENUM` | `NOT NULL, DEFAULT 'OPEN'` | `OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED` |
| `assigned_agent_id` | `UUID` | `FK users(id) ON DELETE SET NULL` | Assigned support representative |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | Last update timestamp |

---

### 2.2 `messages`
Individual communications within a conversation thread.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Globally unique identifier |
| `conversation_id` | `UUID` | `FK conversations(id) ON DELETE CASCADE, INDEX` | Parent conversation |
| `sender_type` | `ENUM` | `NOT NULL, DEFAULT 'CUSTOMER'` | `CUSTOMER`, `AGENT`, `SYSTEM` |
| `sender_name` | `VARCHAR(255)` | `NULLABLE` | Sender display name |
| `content` | `TEXT` | `NOT NULL` | Message body content |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Timestamp sent |

---

### 2.3 `analyses`
Persisted customer intelligence results produced by ML inference.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Globally unique identifier |
| `conversation_id` | `UUID` | `FK conversations(id) ON DELETE CASCADE, INDEX` | Linked conversation |
| `category` | `VARCHAR(100)` | `NULLABLE` | Canonical business category |
| `issue` | `VARCHAR(255)` | `NULLABLE` | Synthesized core customer issue |
| `sentiment` | `VARCHAR(50)` | `NULLABLE` | `POSITIVE`, `NEUTRAL`, `NEGATIVE` |
| `emotion` | `VARCHAR(50)` | `NULLABLE` | Dominant human emotion |
| `priority` | `VARCHAR(50)` | `NULLABLE` | Operational priority (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) |
| `resolution_status` | `VARCHAR(50)` | `NULLABLE` | `RESOLVED`, `UNRESOLVED`, `IN_PROGRESS` |
| `summary` | `TEXT` | `NULLABLE` | Agent briefing summary |
| `recommended_action` | `TEXT` | `NULLABLE` | Primary action recommendation |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Analysis timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | Timestamp updated |

---

### 2.4 `threats`
Persisted security intelligence and threat detection results.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Globally unique identifier |
| `conversation_id` | `UUID` | `FK conversations(id) ON DELETE CASCADE, INDEX` | Linked conversation |
| `threat_detected` | `BOOLEAN` | `NOT NULL, DEFAULT FALSE` | True if phishing/malware detected |
| `threat_type` | `VARCHAR(100)` | `NULLABLE` | Classification of threat |
| `social_engineering_detected` | `BOOLEAN` | `NOT NULL, DEFAULT FALSE` | True if social engineering signals found |
| `techniques` | `JSONB` | `DEFAULT '[]'` | Detected attack techniques |
| `risk_level` | `VARCHAR(50)` | `NULLABLE` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `suspicious_urls` | `JSONB` | `DEFAULT '[]'` | List of extracted suspicious URLs |
| `suspicious_emails` | `JSONB` | `DEFAULT '[]'` | List of suspicious sender/body emails |
| `risk_reasons` | `JSONB` | `DEFAULT '[]'` | Explainability audit reasons |
| `recommended_action` | `TEXT` | `NULLABLE` | Prescribed security action |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Threat detection timestamp |

---

### 2.5 `customer_reviews`
Persisted canonical `CustomerReviewOutput` records — the AI analysis of inbox feedback records, cached per `INBOX-<recordId>` (schema mirrors `app/schemas/review.py`; 40+ columns incl. `review_id`, `source_record_id`, `classification_confidence`, `needs_review`, `sentiment_label`, `sentiment_score`, `keywords` JSON, `summary_text`, cluster fields, `urgency_level`, `resolution_status`, security fields, `overall_risk`, recommendation, model metadata, processing info).

---

## 3. Data Service database (app/data)

The Data API keeps its own separate store — `inbox_dev.db` (SQLite) locally, PostgreSQL in Docker — holding the cleaned inbox dataset:

- **`tickets`**: `id`, `message`, `subject`, `intent`, `issue`, `domain`, `channel`, `technique`, `phishing`, `sender`, `label`, derived `priority` (+ `priority_rank`), `created_at`.
- **`attachments`**: `id`, `ticket_id` (FK, CASCADE), `file_name`, `file_type`, `file_path`, `file_size`, `created_at`.

The Backend's `users` table exists in the ORM but authentication was removed by product decision; no endpoint consumes it. Attachment uploads/metadata are served by the **Data API**, not the Backend.

## 4. Where to look

- ORM definitions: `app/Backend/app/models/` (Backend operational DB), `app/data/backend/models.py` (Data service DB).
- Alembic migrations: `app/Backend/alembic/`.
- Canonical review field-by-field contract: [`ml-contract.md`](ml-contract.md).
