# SOLWIN Frontend Development Prompt — Antigravity

## Project

Build the complete frontend web application for **SOLWIN**, an AI-powered Customer Intelligence + Cybersecurity Operations platform.

The frontend must consume an existing REST API backend. **Do not create mock AI logic in the frontend.** All classification, sentiment analysis, threat detection, risk assessment, summarization, campaign detection, and recommendations must come from backend API responses.

---

## 1. Technology

Use:

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios or Fetch API
- Recharts for analytics
- Lucide React icons

Create clean, reusable components and a dedicated API service layer.

### Suggested Structure

```text
src/
├── components/
│   ├── layout/
│   ├── dashboard/
│   ├── conversations/
│   ├── security/
│   ├── campaigns/
│   ├── analytics/
│   └── common/
│
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   ├── Conversations.tsx
│   ├── ConversationDetails.tsx
│   ├── Threats.tsx
│   ├── ThreatDetails.tsx
│   ├── CampaignRadar.tsx
│   ├── CampaignDetails.tsx
│   ├── CustomerInsights.tsx
│   ├── SecurityAnalytics.tsx
│   └── Settings.tsx
│
├── services/
│   ├── api.ts
│   ├── authApi.ts
│   ├── conversationApi.ts
│   ├── analysisApi.ts
│   ├── securityApi.ts
│   ├── campaignApi.ts
│   └── analyticsApi.ts
│
├── types/
│   ├── auth.ts
│   ├── conversation.ts
│   ├── analysis.ts
│   ├── security.ts
│   └── campaign.ts
│
├── hooks/
├── utils/
├── App.tsx
└── main.tsx
```

---

# 2. Product Design

SOLWIN should look like a combination of:

**Customer Support Intelligence + SOC Dashboard + AI Operations Center**

The interface should feel suitable for a real enterprise environment.

### Visual Theme

- Dark professional interface
- Near-black / charcoal background
- Blue and violet accent lighting
- White/light-gray typography
- Subtle borders
- Glass/soft-card surfaces
- Minimal gradients
- Clean charts
- Minimal animation
- Strong visual hierarchy
- Avoid excessive neon effects
- Avoid a gaming aesthetic
- Avoid unnecessary decorative elements

Prioritize readability, information density, and usability.

---

# 3. Application Layout

After login:

```text
┌─────────────────────────────────────────────────────────────┐
│ SOLWIN                            Search     🔔    User      │
├───────────────┬─────────────────────────────────────────────┤
│               │                                             │
│ Dashboard     │                                             │
│ Conversations │              MAIN CONTENT                   │
│               │                                             │
│ CUSTOMER      │                                             │
│ Intelligence  │                                             │
│               │                                             │
│ SECURITY      │                                             │
│ Threats       │                                             │
│ Campaign Radar│                                             │
│               │                                             │
│ ANALYTICS     │                                             │
│ Customer      │                                             │
│ Security      │                                             │
│               │                                             │
│ Settings      │                                             │
│               │                                             │
└───────────────┴─────────────────────────────────────────────┘
```

### Sidebar

Navigation:

- Dashboard
- Conversations
- Customer Insights
- Threats
- Campaign Radar
- Security Analytics
- Settings

Desktop:
- Persistent sidebar

Tablet:
- Collapsible sidebar

Mobile:
- Drawer navigation

---

# 4. Authentication

## Login Page

Route:

```text
/login
```

Create a professional SOLWIN login page.

Fields:

- Email
- Password
- Remember me
- Sign in

Do not expose admin functionality publicly.

On successful login:

```text
Login
  ↓
Store authentication state/token securely
  ↓
Redirect to /dashboard
```

Handle:

- Invalid credentials
- Backend unavailable
- Session expired
- Validation errors

### Protected Routes

All application pages except `/login` must require authentication.

For `401` responses:

```text
Clear expired authentication
↓
Redirect to /login
```

---

# 5. Dashboard

Route:

```text
/dashboard
```

Consume:

```http
GET /api/v1/dashboard/overview
```

The dashboard is the main landing page.

## KPI Cards

Display:

```text
Total Conversations
Total Complaints
Unresolved
Critical Cases
Threats Detected
High Risk
Critical Threats
Active Campaigns
```

Example layout:

```text
┌────────────────┬────────────────┬────────────────┬────────────────┐
│ Conversations  │ Complaints     │ Unresolved     │ Critical       │
│ 12,842         │ 3,284          │ 487            │ 24             │
└────────────────┴────────────────┴────────────────┴────────────────┘

┌───────────────────────────────┐ ┌───────────────────────────────┐
│ Customer Sentiment            │ │ Security Risk                 │
│                               │ │                               │
│ Positive 32%                  │ │ Low                           │
│ Neutral  41%                  │ │ Medium                        │
│ Negative 27%                  │ │ High                          │
│                               │ │ Critical                      │
└───────────────────────────────┘ └───────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Top Customer Issues                                             │
│                                                                 │
│ Account Access        █████████████                             │
│ Billing               █████████                                 │
│ Technical Issue       ███████                                   │
│ Fraud Concern         █████                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Never hardcode dashboard statistics.**

Use only backend data.

---

# 6. Conversations

Route:

```text
/conversations
```

Consume:

```http
GET /api/v1/conversations
```

Create a searchable conversation table.

## Columns

```text
Customer
Channel
Issue
Category
Sentiment
Priority
Security Risk
Status
Updated
```

Example:

```text
Meera Nair
Email
Account compromise
Account Security
Negative
Critical
Critical
Unresolved
2 min ago
```

## Features

- Search
- Category filter
- Sentiment filter
- Priority filter
- Status filter
- Security-risk filter
- Pagination
- Sorting
- Open conversation details

---

# 7. Conversation Details

Route:

```text
/conversations/:id
```

Consume:

```http
GET /api/v1/conversations/{id}
GET /api/v1/analysis/conversation/{id}
```

Use a two-column layout.

## Left — Conversation

Display:

- Customer information
- Conversation metadata
- Channel
- Conversation timeline
- Customer messages
- Agent messages
- Attachments

Supported channels:

- Email
- Chat
- SMS
- Social
- Phone transcript

Example:

```text
Customer
Meera Nair

Channel
Email

Conversation

Customer:
My account has been compromised...

Agent:
We are reviewing your account...

Customer:
I also received this suspicious link...
```

---

# 8. AI Customer Intelligence

On the conversation details page, display an AI Intelligence panel.

Consume:

```http
GET /api/v1/analysis/conversation/{id}
```

Display:

```text
Category
Issue
Sentiment
Emotion
Priority
Resolution Status
Customer Request
Summary
Recommended Action
```

Example:

```text
┌─────────────────────────────────────┐
│ CUSTOMER INTELLIGENCE               │
│                                     │
│ Category                            │
│ Account Security                    │
│                                     │
│ Issue                               │
│ Potential account compromise       │
│                                     │
│ Sentiment                           │
│ Negative                            │
│                                     │
│ Emotion                             │
│ Fear                                │
│                                     │
│ Priority                            │
│ Critical                            │
│                                     │
│ Status                              │
│ Unresolved                          │
└─────────────────────────────────────┘
```

Use reusable badges:

- SentimentBadge
- PriorityBadge
- StatusBadge

---

# 9. Security Intelligence

Display a dedicated security section on conversation details.

Consume the security analysis returned by the backend.

Display:

```text
Threat Detected
Threat Type
Risk Level
Social Engineering
Techniques
Suspicious URLs
Suspicious Emails
Recommended Action
```

Example:

```text
┌─────────────────────────────────────┐
│ SECURITY INTELLIGENCE               │
│                                     │
│ Threat Detected       YES           │
│ Threat Type           Phishing      │
│ Risk Level            CRITICAL      │
│                                     │
│ Social Engineering    Detected      │
│                                     │
│ Techniques                           │
│ • Urgency                            │
│ • Credential Harvesting              │
│ • OTP Request                        │
└─────────────────────────────────────┘
```

**Never independently determine whether something is a threat in React.**

Render the backend result.

---

# 10. URL Analysis

When the backend returns suspicious URLs, display an expandable URL analysis card.

Fields:

```text
URL
Domain
HTTPS
Domain Reputation
Lookalike Domain
URL Shortener
IP Based URL
Suspicious Pattern
Risk Contribution
```

Example:

```text
Suspicious URL

https://example.com/login

Domain:
example.com

HTTPS:
Yes

Lookalike:
Detected

Risk:
High
```

Only display a malicious/threat determination when the backend provides it.

---

# 11. Email Analysis

Display suspicious email indicators.

Fields:

```text
Sender
Display Name
Email Domain
Expected Domain
Domain Match
Lookalike Domain
Impersonation
Risk
```

Example:

```text
Sender:
support@paypa1-security.example

Domain:
paypa1-security.example

Domain mismatch:
Detected

Impersonation:
Detected
```

---

# 12. Risk Visualization

Create a reusable:

```text
<RiskBadge />
```

Supported levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Create:

```text
<RiskSummary />
```

If the backend provides contributing factors, display them.

Example:

```text
Risk Analysis

Suspicious URL              +25
Lookalike Domain            +25
Credential Request          +20
OTP Request                 +15
Urgency                     +10

Total Risk: 95
Level: CRITICAL
```

If the backend does not return a score, do not invent one.

---

# 13. Threats

Route:

```text
/threats
```

Consume:

```http
GET /api/v1/security/threats
```

Create a SOC-style threat table.

## Columns

```text
Threat ID
Threat Type
Customer
Channel
Risk Level
Threat Detected
Social Engineering
Detected At
Status
```

## Filters

```text
Risk
Threat Type
Date
Status
Channel
```

Possible threat types may include:

```text
Phishing
Credential Theft
Account Takeover
Impersonation
Fraud
Social Engineering
Suspicious Link
```

Use only values returned by the backend.

---

# 14. Threat Details

Route:

```text
/threats/:id
```

Show:

- Threat metadata
- Related conversation
- Threat type
- Risk level
- Detection details
- Suspicious URLs
- Suspicious email indicators
- Social-engineering techniques
- Recommended action
- Detection timeline

Provide a clear escalation/action area if supported by the backend.

---

# 15. Campaign Radar

Route:

```text
/campaigns
```

Consume:

```http
GET /api/v1/campaigns
```

This page visualizes potentially coordinated threats.

Example:

```text
                    CAMPAIGN RADAR

                         ●
                       / | \
                      /  |  \
                     /   |   \
                    ●    ●    ●
                   / \       / \
                  ●   ●     ●   ●

             Potential Campaign #03

             14 conversations
             6 suspicious domains
             3 sender patterns
             4 techniques
```

Create campaign cards containing:

- Campaign ID
- Number of affected conversations
- Common URLs/domains
- Common sender patterns
- Common social-engineering techniques
- Risk level
- First detected
- Last detected
- Status

---

# 16. Campaign Details

Route:

```text
/campaigns/:id
```

Display:

```text
Campaign Overview
        ↓
Related Conversations
        ↓
Common Domains
        ↓
Common Senders
        ↓
Common Techniques
        ↓
Risk Information
        ↓
Timeline
```

Provide links to the related conversation and threat details pages.

---

# 17. Customer Insights

Route:

```text
/insights/customer
```

Consume:

```http
GET /api/v1/insights/customer
```

## Sentiment

Create a chart for:

```text
Positive
Neutral
Negative
```

## Top Issues

Display:

```text
Account Access
Billing
Technical Problems
Fraud
Delivery
Subscription
```

## Priority Distribution

```text
Low
Medium
High
Critical
```

## Resolution

```text
Resolved
Pending
Escalated
Unresolved
```

Add date filters where supported by the API.

---

# 18. Security Analytics

Route:

```text
/analytics/security
```

Consume:

```http
GET /api/v1/analytics/security
```

Display:

```text
Threats Over Time
Risk Distribution
Threat Types
Social Engineering Techniques
Suspicious Domains
Phishing Trends
Campaign Activity
```

Use Recharts.

Charts should have:

- Responsive sizing
- Tooltips
- Legends
- Clear labels
- Empty states
- Loading states

---

# 19. Global Search

Add global search in the top navigation.

Search across:

```text
Customer
Conversation ID
Email
Threat ID
URL
Campaign
Issue
```

Use backend search when available.

Avoid loading the entire dataset into the browser just to perform client-side search.

---

# 20. Attachment / Multimodal UI

Support the backend's attachment and multimodal analysis APIs.

Endpoints:

```http
POST /api/v1/attachments
POST /api/v1/analysis/multimodal
```

Flow:

```text
Customer uploads image/file
        ↓
Upload to backend
        ↓
Backend performs OCR / vision analysis
        ↓
Extracted information
        ↓
Customer + Security Intelligence
        ↓
Display results
```

Frontend responsibilities:

- File picker
- Upload progress
- File preview where appropriate
- Upload validation
- Error handling
- Analysis loading state
- Display backend analysis

Do not perform the AI analysis directly in the browser.

---

# 21. API Layer

Create a central API client.

Example:

```typescript
import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});
```

Attach authentication to requests.

Create separate service functions:

```text
login()

getDashboardOverview()

getConversations()

getConversation(id)

getConversationAnalysis(id)

analyzeConversation(id)

getThreats()

getThreat(id)

analyzeSecurity(data)

getCampaigns()

getCampaign(id)

getCustomerInsights()

getCustomerAnalytics()

getSecurityAnalytics()

uploadAttachment()

analyzeMultimodal()
```

Never put API requests directly into large page components.

---

# 22. Environment Variables

Create:

```text
.env.example
```

with:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

The frontend must work with different backend URLs without modifying source code.

---

# 23. TypeScript API Types

Create strongly typed interfaces.

Example:

```typescript
export interface CustomerIntelligence {
  category: string;
  issue: string;
  sentiment: string;
  emotion?: string;
  priority: string;
  resolution_status: string;
  customer_request?: string;
  summary: string;
  recommended_action?: string;
}

export interface SecurityIntelligence {
  threat_detected: boolean;
  threat_type?: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  social_engineering?: boolean;
  techniques: string[];
  suspicious_urls: SuspiciousUrl[];
  suspicious_emails: SuspiciousEmail[];
  recommended_action?: string;
}
```

Create interfaces matching the actual backend responses.

Do not use `any` unnecessarily.

---

# 24. Loading States

Every API-driven page must have loading states.

Use:

- Skeleton cards
- Skeleton tables
- Loading indicators
- Disabled buttons during requests

Never show a blank page while waiting for the backend.

---

# 25. Error Handling

Create reusable error components.

Handle:

```text
400
401
403
404
422
429
500
Network Error
Timeout
```

### 401

```text
Clear authentication
↓
Redirect to /login
```

### 500

Display:

```text
Something went wrong.
Please try again.
```

Never expose backend stack traces to users.

---

# 26. Empty States

Create meaningful empty states.

### Threats

```text
No threats detected

No security threats match the selected filters.
```

### Campaigns

```text
No active campaigns

The system has not identified any coordinated threat patterns.
```

### Conversations

```text
No conversations found

Try changing your search or filters.
```

---

# 27. Reusable Components

Create:

```text
<KpiCard />

<RiskBadge />

<PriorityBadge />

<SentimentBadge />

<StatusBadge />

<ThreatCard />

<ConversationCard />

<ConversationTimeline />

<AiInsightPanel />

<SecurityInsightPanel />

<UrlAnalysisCard />

<EmailAnalysisCard />

<CampaignCard />

<AnalyticsChart />

<DataTable />

<FilterBar />

<SearchBar />

<EmptyState />

<LoadingSkeleton />

<ErrorState />

<ProtectedRoute />
```

Maintain consistent styling and behavior.

---

# 28. Backend API Contract

The frontend should support these endpoints:

```text
POST   /api/v1/auth/login

GET    /api/v1/dashboard/overview

GET    /api/v1/conversations
POST   /api/v1/conversations
GET    /api/v1/conversations/{id}

POST   /api/v1/analysis/conversation/{id}
GET    /api/v1/analysis/conversation/{id}

POST   /api/v1/security/analyze
GET    /api/v1/security/threats
GET    /api/v1/security/threats/{id}

GET    /api/v1/campaigns
GET    /api/v1/campaigns/{id}

GET    /api/v1/insights/customer

GET    /api/v1/analytics/customer
GET    /api/v1/analytics/security

POST   /api/v1/attachments
POST   /api/v1/analysis/multimodal
```

If an endpoint is temporarily unavailable, show an appropriate loading/error/empty state instead of breaking the application.

---

# 29. Main Demo Flow

The frontend must support this complete demonstration:

## Step 1 — Login

```text
/login
```

User signs in.

## Step 2 — Dashboard

```text
/dashboard
```

Show:

- Customer activity
- AI insights
- Threat statistics
- Critical cases
- Campaign activity

## Step 3 — Conversations

```text
/conversations
```

Select a suspicious conversation.

## Step 4 — Customer Intelligence

Show:

```text
Customer message
        ↓
AI classification
        ↓
Sentiment
        ↓
Emotion
        ↓
Issue
        ↓
Summary
        ↓
Priority
        ↓
Resolution status
```

## Step 5 — Security Intelligence

Show:

```text
Threat detection
        ↓
Threat type
        ↓
Suspicious URL
        ↓
Suspicious email
        ↓
Social engineering
        ↓
Risk level
        ↓
Recommended action
```

## Step 6 — Campaign Radar

Show related suspicious conversations grouped into a potential campaign.

## Step 7 — Security Analytics

Show:

```text
Threat trends
Risk distribution
Threat types
Social-engineering techniques
Campaign activity
```

---

# 30. Critical Architecture Rule

The frontend is the **presentation and interaction layer**.

Do NOT implement these in React:

```text
LLM classification
Sentiment calculation
Risk scoring
Phishing classification
Campaign detection
Threat determination
```

The backend is responsible for these operations.

The frontend should simply render backend results.

Example:

```json
{
  "risk_level": "HIGH",
  "threat_detected": true,
  "sentiment": "Negative"
}
```

React should display these values, not calculate them.

---

# 31. Security and UX Requirements

Implement:

- Protected routes
- Authentication handling
- Input validation
- API error handling
- Safe rendering of user-provided text
- File upload validation
- Request loading states
- Session expiration handling
- Accessible buttons and forms
- Keyboard-friendly navigation
- Responsive layouts
- Clear focus states

Never expose:

- API secrets
- LLM API keys
- Database credentials
- Backend environment variables

in frontend code.

---

# 32. Performance

For large datasets:

- Use pagination
- Avoid unnecessary API requests
- Debounce search inputs
- Lazy-load heavy pages/components where useful
- Use memoization only when it provides a real benefit
- Avoid rendering thousands of rows at once

---

# 33. Final Acceptance Criteria

The generated frontend is complete when:

- [ ] Login works
- [ ] Protected routes work
- [ ] Dashboard consumes backend data
- [ ] Conversation list works
- [ ] Conversation details work
- [ ] AI customer intelligence renders backend results
- [ ] Security intelligence renders backend results
- [ ] URL analysis is displayed
- [ ] Email analysis is displayed
- [ ] Risk levels are displayed
- [ ] Threat list works
- [ ] Threat details work
- [ ] Campaign Radar works
- [ ] Campaign details work
- [ ] Customer Insights works
- [ ] Security Analytics works
- [ ] Attachments can be uploaded
- [ ] Multimodal analysis results can be displayed
- [ ] Search and filters work
- [ ] Loading states exist
- [ ] Error states exist
- [ ] Empty states exist
- [ ] Mobile layout works
- [ ] No AI logic is hardcoded in the frontend
- [ ] No fake dashboard statistics are hardcoded
- [ ] API base URL is configurable
- [ ] TypeScript types match backend responses

---

# 34. Final Product Goal

The final SOLWIN frontend should feel like a **real enterprise AI Customer Intelligence + Cybersecurity Operations platform**.

The user should be able to move naturally through:

```text
LOGIN
  ↓
DASHBOARD
  ↓
CONVERSATIONS
  ↓
CONVERSATION DETAILS
  ↓
CUSTOMER INTELLIGENCE
  +
SECURITY INTELLIGENCE
  ↓
THREAT DETAILS
  ↓
CAMPAIGN RADAR
  ↓
SECURITY ANALYTICS
```

The application must prioritize **clarity, explainability, responsiveness, and real backend integration** over decorative UI.
