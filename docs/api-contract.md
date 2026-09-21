# Backend API Contract & Frontend Integration Specification

## 1. Overview
This document defines the Backend REST API exposed to clients and dashboards. It forms the canonical interface contract for Team D (Frontend).

**Base Prefix**: `/api/v1`  
**Authentication**: none (removed by product decision; no endpoint requires a token)

---

## 2. API Endpoints

### 2.1 Conversations & Messages

#### `POST /api/v1/conversations`
- **Description**: Create a new customer conversation.
- **Request**:
```json
{
  "customer_name": "Alice Smith",
  "customer_email": "alice@example.com",
  "channel": "CHAT",
  "subject": "Delayed Order #89211",
  "initial_message": "My order has been delayed for 5 days. Please update status."
}
```
- **Response**: `201 Created` with full conversation object including stable reference `CONV-000101`.

#### `GET /api/v1/conversations`
- **Description**: List conversations with pagination and filtering.
- **Query Params**: `skip=0`, `limit=50`, `status=OPEN`, `channel=CHAT`, `search=delayed`
- **Response**:
```json
{
  "total": 142,
  "skip": 0,
  "limit": 50,
  "items": [
    {
      "id": "c4d3e2a1-...",
      "conversation_reference": "CONV-000101",
      "customer_name": "Alice Smith",
      "channel": "CHAT",
      "status": "OPEN",
      "subject": "Delayed Order #89211",
      "created_at": "2026-09-18T20:00:00Z"
    }
  ]
}
```

#### `GET /api/v1/conversations/{conversation_id}`
- **Description**: Retrieve detailed conversation with complete message thread and latest intelligence results.

---

### 2.2 Unified Intelligence Analysis

#### `POST /api/v1/analyze`
- **Description**: Trigger complete intelligence analysis on a conversation, persist results in `analyses` and `threats`, and return the unified assessment.
- **Request**:
```json
{
  "conversation_id": "c4d3e2a1-..."
}
```
- **Response**: `200 OK` matching unified schema.

#### `GET /api/v1/analyze/conversation/{conversation_id}`
- **Description**: Retrieve latest persisted analysis and threat records without re-invoking inference.

---

### 2.3 Customer Review Intelligence (inbox AI)

#### `POST /api/v1/reviews`
- **Description**: Analyze an inbox feedback record via the ML service tiered pipeline and persist the canonical `CustomerReviewOutput` (cached per `source_record_id`, e.g. `INBOX-1414`).
- **Request**:
```json
{
  "source_record_id": "INBOX-1414",
  "domain": "E-commerce/Retail",
  "channel": "Email",
  "subject": "Payment issue",
  "message": "I did not receive my refund..."
}
```
- **Response**: `200 OK` with the full 13-section canonical review (classification, sentiment, keywords, summary, clustering, urgency, resolution, security, overall_risk, recommendation, model_metadata, processing).

#### `GET /api/v1/reviews`
- **Description**: List persisted review analyses (paginated).

#### `GET /api/v1/reviews/{review_id}`
- **Description**: Retrieve one persisted review by its `review_id`.

---

### 2.4 Security Intelligence

#### `GET /api/v1/security/threats`
- **Description**: Paginated list of detected threats (`threat_detected` records with type, techniques, risk level, evidence).

#### `GET /api/v1/security/threats/{threat_id}`
- **Description**: Full detail for one threat.

#### `POST /api/v1/security/analyze`
- **Description**: Ad-hoc security analysis of submitted content (URL/email extraction, risk scoring) — persists nothing.

#### `POST /api/v1/security/conversation/{conversation_id}`
- **Description**: Run and persist the security scan for a conversation.

---

### 2.5 Dashboard & Analytics KPIs

#### `GET /api/v1/dashboard/overview`
- **Description**: Pre-aggregated metrics for high-level dashboard display.
- **Response**:
```json
{
  "total_conversations": 1250,
  "open_conversations": 340,
  "in_progress_conversations": 180,
  "resolved_conversations": 730,
  "total_threats_detected": 42,
  "high_risk_threats": 14,
  "critical_risk_threats": 3,
  "sentiment_breakdown": {
    "POSITIVE": 280,
    "NEUTRAL": 490,
    "NEGATIVE": 480
  },
  "category_breakdown": {
    "PAYMENT_TRANSACTION_ISSUE": 310,
    "DELIVERY_SHIPPING_PROBLEM": 420,
    "SECURITY_CONCERN": 42,
    "OTHER": 478
  }
}
```

#### `GET /api/v1/analytics/customer`
- **Description**: Deep breakdown of categories, priority levels, resolution statuses, and top recurring issues.

#### `GET /api/v1/analytics/top-issues`
- **Description**: Ranked most-reported issues with counts.

#### `GET /api/v1/analytics/trends?days=30`
- **Description**: Daily conversation volume trend over the trailing window.

#### `GET /api/v1/analytics/security`
- **Description**: Security analytics distributions (risk levels, threat types).

#### `GET /api/v1/analytics/security/recent-threats`
- **Description**: Latest threat events.

#### `GET /api/v1/analytics/security/trends?days=30`
- **Description**: Daily threat-event trend over the trailing window (counts only days with actual threat events).

---

## 3. Conversation lifecycle endpoints

| Method & Path | Purpose |
|---|---|
| `GET /api/v1/conversations/{id}` | Detail incl. full message thread and latest intelligence |
| `PATCH /api/v1/conversations/{id}` | Update status/assignment |
| `DELETE /api/v1/conversations/{id}` | Delete conversation (cascades) |
| `POST /api/v1/conversations/{id}/messages` | Append a message to the thread |
| `GET /api/v1/conversations/{id}/messages` | List messages |
| `GET /api/v1/unified/conversation/{id}` | Unified intelligence view (convenience) |

---

## 4. Conventions

- All list endpoints return `{total, skip, limit, items}` pagination envelopes.
- Errors follow FastAPI semantics: `422` validation detail arrays, `404` unknown ids (ids are UUIDs — display references like `CONV-000003` are not valid ids).
- Enums are uppercase strings (`OPEN`, `NEGATIVE`, `CRITICAL`, ...).
