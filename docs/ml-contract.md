# Canonical ML Service Integration Contract

## 1. Primary Endpoint Specification

**Method**: `POST`  
**Path**: `/api/v1/analyze`  
**Content-Type**: `application/json`

---

## 2. Request Payload Schema

```json
{
  "complaint_id": "CMP-2024-001",
  "complaint": {
    "subject": "Unauthorized charge and suspicious login link",
    "message": "I was charged $450 without authorization. The SMS linked to http://192.168.1.1/login. Please refund immediately!"
  },
  "include_cluster": true,
  "include_urgency": true,
  "include_resolution": true,
  "include_recommendation": true,
  "include_security": true,
  "include_summary": true,
  "prefer_llm": false
}
```

### Request Fields
- `complaint_id` *(optional string)*: Unique identifier originating from source dataset or client conversation reference. Preserved in response.
- `complaint.subject` *(optional string)*: Complaint title/subject line (max 2,000 chars).
- `complaint.message` *(optional string)*: Main complaint body (max 10,000 chars). *At least one of subject or message is required.*
- Feature Toggles *(booleans, default true)*: `include_cluster`, `include_urgency`, `include_resolution`, `include_recommendation`, `include_security`, `include_summary`.
- `prefer_llm` *(boolean, default false)*: Toggle LLM fallback for summarization when available.

---

## 3. Response Payload Schema

```json
{
  "complaint_id": "CMP-2024-001",
  "classification": {
    "category": "PAYMENT_TRANSACTION_ISSUE",
    "confidence": 0.942,
    "probabilities": {
      "PAYMENT_TRANSACTION_ISSUE": 0.942,
      "BILLING_PROBLEM": 0.031,
      "SECURITY_CONCERN": 0.012
    },
    "needs_review": false,
    "model_name": "complaint_classifier",
    "model_version": "v1.0.0",
    "fine_grained_intent": "Online Payment Issues"
  },
  "cluster": {
    "cluster_id": 3,
    "cluster_name": "Cluster 3: Payment & Transaction Failures",
    "dominant_category": "PAYMENT_TRANSACTION_ISSUE",
    "distance": 0.412,
    "keywords": ["payment", "deducted", "failed", "gateway", "charged"]
  },
  "urgency": {
    "urgency": "HIGH",
    "confidence": 0.85,
    "signals": ["monetary_deduction", "unauthorized_charge"],
    "reasons": ["Detected financial deduction / unauthorized charge indicators."]
  },
  "resolution": {
    "status": "UNRESOLVED",
    "confidence": 0.80,
    "signals": ["pending_customer_complaint"],
    "pending_items": ["Refund processing required"]
  },
  "security": {
    "urls": [
      {
        "url": "http://192.168.1.1/login",
        "normalized_url": "http://192.168.1.1/login",
        "domain": "192.168.1.1",
        "risk_level": "HIGH",
        "risk_score": 0.80,
        "signals": ["ip_address_host", "suspicious_keyword_login"],
        "provider": "solwin_security_engine",
        "analyzed_at": "2026-09-18T21:40:00Z"
      }
    ],
    "emails": [],
    "aggregate_risk": "HIGH",
    "requires_quarantine": true,
    "risk_reasons": ["Direct IP address hostname detected in URL", "Phishing login path keyword detected"]
  },
  "recommendation": {
    "primary_action": "ESCALATE_TO_SECURITY_TEAM",
    "secondary_actions": ["ESCALATE_TO_PAYMENT_TEAM"],
    "rationale": "High security risk detected alongside high financial urgency.",
    "matched_rule_id": "RULE_CRITICAL_SECURITY_ESCALATION"
  },
  "summary": {
    "customer_issue": "Unauthorized monetary deduction of $450 and receipt of phishing link.",
    "actions_taken": [],
    "pending_actions": ["Investigate transaction authenticity", "Quarantine link http://192.168.1.1/login"],
    "resolution_status": "UNRESOLVED",
    "entities_extracted": {
      "amounts": ["$450"],
      "order_ids": [],
      "urls": ["http://192.168.1.1/login"]
    },
    "summary_mode": "extractive",
    "key_phrases": ["unauthorized charge", "phishing link"]
  },
  "processing_time_ms": 3.82,
  "warnings": []
}
```

---

## 4. Canonical Enums Reference

### Business Categories (`classification.category`)
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

### Urgency Levels (`urgency.urgency`)
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

### Resolution Statuses (`resolution.status`)
- `RESOLVED`
- `UNRESOLVED`
- `PARTIALLY_RESOLVED`
- `UNKNOWN`

### Security Risk Levels (`security.aggregate_risk`, `security.urls[].risk_level`)
- `SAFE`
- `LOW`
- `MEDIUM`
- `HIGH`

### Recommended Action Types (`recommendation.primary_action`)
- `REQUEST_MORE_INFORMATION`
- `ESCALATE_TO_PAYMENT_TEAM`
- `ESCALATE_TO_SECURITY_TEAM`
- `ESCALATE_TO_TECHNICAL_TEAM`
- `ESCALATE_TO_BILLING_TEAM`
- `ESCALATE_TO_DELIVERY_TEAM`
- `INITIATE_REFUND_REVIEW`
- `VERIFY_CUSTOMER_IDENTITY`
- `RESET_ACCOUNT_ACCESS`
- `MONITOR`
- `STANDARD_SUPPORT_RESPONSE`
- `HUMAN_REVIEW`
