---
title: Components
---

The SwarmOps frontend is built with React, TypeScript, and Tailwind CSS. Components are organized by feature area and fully styled for the RM console experience. {% .lead %}

---

## Component structure

```shell
frontend/src/components/
├── conversation/    # Conversation view components
├── sidebar/         # Navigation sidebar
├── memory/          # Client memory panel
└── shared/          # Reusable UI primitives
```

---

## Key components

### Conversation view

Displays the agent analyses and moderator synthesis for a single event. Components include:

- **Message list** — Renders agent analysis messages in chronological order
- **Agent status indicators** — Shows which agents are analyzing vs. complete
- **Risk level badges** — Color-coded by severity (critical, high, medium, low)
- **Moderator summary** — Consensus, dissent, key decisions, and next steps

### Sidebar

- **Conversation list** — All events sorted by risk severity
- **Status filters** — Live, awaiting decision, concluded
- **Client grouping** — Events grouped by client name

### Memory panel

- **Client memory viewer** — Displays the per-client markdown memory
- **Memory edit proposals** — Shows suggested updates from the system (requires RM approval)

### Action queue

- **Action items** — Buttons styled by variant (primary, secondary, danger)
- **Two-step confirmation** — Actions require confirmation before executing
- **Override justification** — Text input required when overriding agent recommendations

---

## Styling

All components use Tailwind CSS utility classes:

- Dark mode support via `dark:` variants
- Responsive layout with `sm:`, `md:`, `lg:` breakpoints
- Risk-level color coding:
  - Critical: red (`bg-red-500`)
  - High: orange (`bg-orange-500`)
  - Medium: yellow (`bg-yellow-500`)
  - Low: green (`bg-green-500`)

---

## Data source

{% callout type="warning" title="Using mock data" %}
The frontend currently uses mock data from `frontend/src/data/mockData.ts`. API integration with React Query hooks and the SSE client is on the build roadmap.
{% /callout %}

### Mock data structure

The mock data in `mockData.ts` provides sample conversations that exercise the full UI:

- Wire transfer events with high-risk agent analyses
- Velocity alerts with mixed agent assessments
- Security alerts with moderator dissent

---

## App entry point

**File:** `frontend/src/App.tsx`

The main App component renders the sidebar, conversation view, and memory panel in a three-column layout. It currently reads from mock data rather than making API calls.

---

## Future: API integration

The planned API integration will use:

- **React Query** for data fetching and caching
- **EventSource** or fetch-based SSE client for streaming
- **Optimistic updates** for RM action submissions
