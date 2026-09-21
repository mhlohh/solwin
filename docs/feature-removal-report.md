# Feature Removal Report: Cleanup of Unsupported Features & APIs

**Project:** Customer Complaint ML & Security Intelligence Platform  
**Date:** 2026-09-19  
**Status:** COMPLETE & VALIDATED  

---

## 1. Features Removed

1. **Cyber Threat Campaigns & Campaign Radar:**
   - Campaign correlation logic that grouped threats into adversary clusters.
   - Campaign status lifecycle management (ACTIVE, MONITORED, RESOLVED).
   - Multi-wave campaign telemetry radar.
2. **Message Attachments & Multimodal Vision/OCR:**
   - Attachment uploading, local storage, validation, and retrieval endpoints.
   - Multimodal OCR analysis loop previously integrated into `UnifiedIntelligenceService`.
   - Message and Conversation model attachment foreign keys and cascading relationships.

---

## 2. APIs Removed

### Backend Endpoints Removed
- `POST /api/v1/conversations/{conversation_id}/messages/{message_id}/attachments`
- `GET /api/v1/attachments/{attachment_id}`
- `DELETE /api/v1/attachments/{attachment_id}`
- `POST /api/v1/analysis/multimodal`
- `GET /api/v1/campaigns`
- `GET /api/v1/campaigns/{id}`
- `PATCH /api/v1/campaigns/{id}/status`
- `GET /api/v1/campaigns/radar`

### ML Service Status
- Confirmed ML Service does not host any application-level CRUD, auth, campaigns, attachments, or redundant customer/security analytics endpoints.
- Added `POST /api/v1/analyze/batch` to fulfill batch dataset processing requirements.

---

## 3. Database Objects Removed

1. **Models Deleted:**
   - `app/Backend/app/models/campaign.py` (`Campaign` model).
   - `app/Backend/app/models/attachment.py` (`Attachment` model).
2. **Schema & Model Relationships Removed:**
   - Removed `campaign_id` foreign key and `campaign` relationship from `Threat` model (`app/Backend/app/models/threat.py`).
   - Removed `attachments` relationship from `Conversation` model (`app/Backend/app/models/conversation.py`).
   - Removed `attachments` relationship from `Message` model (`app/Backend/app/models/message.py`).
   - Removed `CampaignStatus` from `app/Backend/app/models/enums.py`.

---

## 4. Tests Removed

1. `app/Backend/tests/test_campaigns.py` (25 tests covering campaign correlation and lifecycle).
2. `app/Backend/tests/test_attachments.py` (22 tests covering attachment storage and multimodal analysis).
3. Updated `app/Backend/tests/test_models_and_schemas.py` to assert that `campaigns` and `attachments` tables are absent from metadata.

---

## 5. Frontend References Removed

1. **Pages & Components Deleted:**
   - `src/pages/CampaignRadar.tsx`
   - `src/pages/CampaignDetails.tsx`
   - `src/components/campaigns/CampaignCard.tsx`
   - `src/components/conversations/AttachmentUploader.tsx`
2. **Services & Types Deleted:**
   - `src/services/campaignApi.ts`
   - `src/types/campaign.ts`
   - Removed `uploadAttachment` and `analyzeMultimodal` from `src/services/analysisApi.ts`.
   - Removed `MultimodalAnalysisResult` from `src/types/analysis.ts`.
   - Removed `mockCampaigns` from `src/services/mockData.ts`.
3. **UI Updates:**
   - In `src/App.tsx`: Removed `/campaigns` and `/campaigns/:id` routes.
   - In `src/components/layout/Sidebar.tsx`: Removed `Campaign Radar` navigation item.
   - In `src/components/layout/Navbar.tsx`: Removed `CMP-` search prefix routing and campaign alert card.
   - In `src/pages/Dashboard.tsx`: Removed `CAMPAIGNS` header button, replaced `Correlated Campaigns` card with `Critical Escalations`, and redirected bottom quick-link to `Threat Intelligence Directory`.
   - In `src/pages/ConversationDetails.tsx`: Removed `<AttachmentUploader />` component.

---

## 6. Dependencies Removed

- No obsolete external Python packages were required to be uninstalled; all core dependencies (`pydantic`, `fastapi`, `sqlalchemy`, `pytest`) are actively used by the remaining complaint intelligence platform.

---

## 7. APIs Retained

### Backend API Surface (`:8000`)
- `GET /health`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/conversations`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{id}`
- `PATCH /api/v1/conversations/{id}`
- `DELETE /api/v1/conversations/{id}`
- `GET /api/v1/conversations/{id}/messages`
- `POST /api/v1/conversations/{id}/messages`
- `POST /api/v1/security/analyze`
- `GET /api/v1/security/conversation/{id}`
- `POST /api/v1/analyze`
- `POST /api/v1/analyze/message`
- `GET /api/v1/analyze/conversation/{id}`
- `GET /api/v1/dashboard/overview`
- `GET /api/v1/analytics/customer`
- `GET /api/v1/analytics/customer/top-issues`
- `GET /api/v1/analytics/customer/trends`
- `GET /api/v1/analytics/security`
- `GET /api/v1/analytics/security/recent-threats`
- `GET /api/v1/analytics/security/trends`

---

## 8. ML APIs Retained (`:8001`)

- `GET /health`
- `GET /ready`
- `GET /api/v1/models`
- `GET /api/v1/capabilities`
- `POST /api/v1/analyze` (Unified pipeline)
- `POST /api/v1/analyze/batch` (Batch dataset pipeline)
- Internal developer testing endpoints: `/api/v1/classify`, `/api/v1/cluster`, `/api/v1/cluster/batch`, `/api/v1/clusters`, `/api/v1/analytics/frequency`, `/api/v1/urgency`, `/api/v1/resolution`, `/api/v1/recommend`, `/api/v1/url/analyze`, `/api/v1/email/analyze`, `/api/v1/summarize`.

---

## 9. Test Results

- **Backend Pytest:**
  ```
  105 passed in 3.12s
  ```
- **ML Services Pytest:**
  ```
  129 passed in 8.08s (including test_unified_analyze_batch)
  ```
- **Frontend Build (`tsc -b && vite build`):**
  ```
  built in 2.15s with 0 errors
  ```

---

## 10. Remaining Known Limitations

- Real live mailbox synchronization (IMAP/SMTP/Gmail API) is omitted by specification; the platform is purely dataset-driven.
- Image OCR is replaced with rich text analysis on complaint content.
