# Backend API Contract & Frontend Integration Specification

## 1. Overview
This document defines the Backend REST API exposed to clients and dashboards. It forms the canonical interface contract for Team D (Frontend).

**Base Prefix**: `/api/v1`  
**Authentication**: Bearer JWT (`Authorization: Bearer <token>`)

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

### 2.3 Attachments & Evidence Handling

#### `POST /api/v1/attachments/upload`
- **Description**: Upload attachment for a conversation message.
- **Content-Type**: `multipart/form-data`
- **Validation**: Strict MIME verification for `application/pdf`, `image/png`, `image/jpeg`.
- **Security**: Cross-platform path traversal sanitization and SHA-256 integrity verification.

---

### 2.4 Threat Campaigns & Radar

#### `GET /api/v1/campaigns`
- **Description**: Retrieve active correlated threat campaigns.
- **Response**:
```json
[
  {
    "id": "e1f2a3b4-...",
    "campaign_name": "CAMPAIGN-PAYPAL-PHISHING-01",
    "status": "ACTIVE",
    "risk_level": "HIGH",
    "threat_count": 8,
    "indicators": {
      "urls": ["http://paypa1-security.example/login"],
      "domains": ["paypa1-security.example"]
    }
  }
]
```

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
