# Database Schema Documentation

## 1. Overview
The database backend is built with **PostgreSQL 15** and **SQLAlchemy 2.0**. All schema definitions support strict typing, foreign key constraints with cascade rules, and automated indexing on query-heavy columns.

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
| `campaign_id` | `UUID` | `FK campaigns(id) ON DELETE SET NULL, INDEX` | Associated threat campaign |
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

### 2.5 `attachments`
Metadata for uploaded files linked to messages.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | Globally unique identifier |
| `conversation_id` | `UUID` | `FK conversations(id) ON DELETE CASCADE, INDEX` | Parent conversation |
| `message_id` | `UUID` | `FK messages(id) ON DELETE CASCADE, INDEX` | Linked message |
| `original_filename` | `VARCHAR(255)` | `NOT NULL` | Sanitized filename |
| `content_type` | `VARCHAR(100)` | `NOT NULL` | Verified MIME type (`application/pdf`, `image/png`, `image/jpeg`) |
| `file_size` | `BIGINT` | `NOT NULL` | File size in bytes |
| `storage_key` | `VARCHAR(512)` | `UNIQUE, INDEX, NOT NULL` | Safe local storage key |
| `checksum` | `VARCHAR(64)` | `INDEX, NOT NULL` | SHA-256 integrity digest |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Upload timestamp |
