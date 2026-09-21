# Solwin Frontend — Operator Console

React + TypeScript + Vite + Tailwind CSS operator console for the Solwin customer intelligence platform. Every page consumes live APIs — there are no mock data paths.

**Ports:** `5173` (Vite dev) · `8080` (nginx in Docker, which also reverse-proxies both APIs)

## Pages

| Route | Page | Data sources |
|---|---|---|
| `/` | Dashboard | Backend `/dashboard/overview` (merges queue metrics + Data API dataset stats) |
| `/inbox` | Inbox (20,862-record feedback queue) | Data API `/tickets`, `/tickets/facets`, `/tickets/{id}`; AI card via Backend `/reviews/INBOX-{id}` |
| `/conversations` | Conversations queue + detail | Backend `/conversations`, `/analyze` |
| `/threats` | Threats (engine events + dataset phishing tab) | Backend `/security/threats`; Data API `/tickets?phishing=true` |
| `/security-analytics` | Security Analytics | Backend `/analytics/security*` + Data API `/tickets/stats` |
| `/customer-insights` | Customer Insights | Backend `/analytics/customer*` + Data API `/tickets/stats` |

## Structure

```text
src/
├── components/    # shared UI (layout, cards, badges, charts)
├── pages/         # one module per route (above)
├── services/      # typed API clients: api.ts (Backend), inboxApi.ts (Data API)
├── types/         # mirrors of the Backend Pydantic contracts
└── index.css      # design tokens (light default, dark via html.dark)
```

## Development

```bash
cd app/frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # production bundle (nginx serves it in Docker)
```

API base URLs are env-driven: `VITE_API_BASE_URL` (Backend, default `/api/v1`) and `VITE_DATA_API_BASE_URL` (Data API, default `/data-api`). In dev, the Vite proxy forwards both to `:8001` / `:8002`; in Docker, nginx does the same so the browser only ever talks to one origin.

## Design system

Practical operator-console aesthetic: neutral surfaces with color reserved for meaning (status/risk), dense readable tables, sticky reading-pane layouts, dark mode via class strategy. Tokens live in `src/index.css`.
