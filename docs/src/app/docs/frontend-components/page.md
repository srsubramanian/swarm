---
title: Components
---

The SwarmOps frontend is built with React, TypeScript, and Tailwind CSS. Components are organized by feature area and fully styled for the RM console experience. {% .lead %}

---

## Component structure

```shell
frontend/src/
├── components/
│   ├── conversation/    # Conversation view components
│   ├── layout/          # AppShell layout
│   ├── sidebar/         # Navigation sidebar
│   ├── memory/          # Client memory panel
│   ├── shared/          # Reusable UI primitives
│   └── ScenarioPanel.tsx  # Scenario submission
├── hooks/               # React Query hooks
│   ├── useConversations.ts
│   ├── useConversation.ts
│   ├── useDecision.ts
│   ├── useScenarios.ts
│   └── useSSE.ts
└── types/               # TypeScript interfaces
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

- **Queue list** — All conversations with pending count badge
- **Queue items** — Client name, title, risk badge, agent icons, message count, actioned status
- **Scenario panel** — Submit pre-built scenarios with loading state

### Memory panel

- **Client memory viewer** — Displays the per-client markdown memory
- **Memory edit proposals** — Shows suggested updates from the system (requires RM approval)

### Action bar

- **Action items** — Buttons styled by variant (primary, secondary, danger)
- **Two-step confirmation** — Actions require confirmation click before executing
- **Justification input** — Text input shown for danger-variant actions
- **Loading state** — Spinner shown during decision mutation (`isPending`)
- **Actioned state** — Shows green checkmark with the selected action label

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

The frontend fetches all data from the backend API via React Query hooks. See the [React Query hooks](/docs/frontend-hooks) page for details.

- **`useConversations`** — Polls `GET /api/conversations` every 5 seconds
- **`useDecision`** — `POST /api/decisions/{id}` mutation with query invalidation
- **`useScenarios`** — Fetches and submits scenarios via queue API
- **`useSSE`** — Fetch-based SSE client for streaming updates

---

## App entry point

**File:** `frontend/src/App.tsx`

Wraps `AppShell` in a `QueryClientProvider` for React Query.

**File:** `frontend/src/components/layout/AppShell.tsx`

The main layout component uses `useConversations()` for the sidebar list, `useDecision()` for action submissions, and manages view mode, selected conversation, and memory drawer state.

---

## ScenarioPanel

**File:** `frontend/src/components/ScenarioPanel.tsx`

Displays available scenarios in the sidebar footer. Uses `useScenarios()` to fetch the list and `useSubmitScenario()` to submit. Shows a loading spinner while the pipeline runs.
