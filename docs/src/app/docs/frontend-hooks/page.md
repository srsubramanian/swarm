---
title: React Query hooks
---

The frontend uses React Query (`@tanstack/react-query`) for data fetching, caching, and mutations. Custom hooks encapsulate all API interactions. {% .lead %}

---

## Setup

The `QueryClientProvider` wraps the app in `App.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell />
    </QueryClientProvider>
  );
}
```

---

## useConversations

**File:** `frontend/src/hooks/useConversations.ts`

Fetches all conversations with automatic polling.

```typescript
export function useConversations() {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: () => fetch('/api/conversations').then(r => r.json()),
    refetchInterval: 5000,  // Poll every 5 seconds
  });
}
```

Returns `{ data: Conversation[], isLoading, error }`.

---

## useConversation

**File:** `frontend/src/hooks/useConversation.ts`

Fetches a single conversation by ID.

```typescript
export function useConversation(id: string | null) {
  return useQuery({
    queryKey: ['conversation', id],
    queryFn: () => fetch(`/api/conversations/${id}`).then(r => r.json()),
    enabled: !!id,
  });
}
```

---

## useDecision

**File:** `frontend/src/hooks/useDecision.ts`

Mutation for submitting RM decisions. Invalidates conversation queries on success.

```typescript
export function useDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, optionId, action, justification }: DecisionPayload) =>
      fetch(`/api/decisions/${conversationId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          option_id: optionId,
          action,
          justification,
        }),
      }).then(r => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}
```

The mutation body uses `snake_case` keys to match the backend `DecisionRequest` schema.

---

## useScenarios

**File:** `frontend/src/hooks/useScenarios.ts`

Fetches available scenarios and provides a mutation for queue submission.

```typescript
export function useScenarios() {
  return useQuery({
    queryKey: ['scenarios'],
    queryFn: () => fetch('/api/queue/scenarios').then(r => r.json()),
  });
}

export function useSubmitScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scenario: string) =>
      fetch('/api/queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
      }).then(r => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}
```

---

## useSSE

**File:** `frontend/src/hooks/useSSE.ts`

Fetch-based SSE client for streaming agent updates.

```typescript
export function useStreamingAnalysis(
  scenario: string,
  onEvent: (event: SSEEvent) => void
) {
  // POST to /api/queue/stream
  // Parse ReadableStream with TextDecoder
  // Emit: start, agent_complete (x3), moderator_complete, done
  // On done: invalidate conversations query
}
```

Uses the Fetch API with `ReadableStream` and `TextDecoder` to parse SSE events — no `EventSource` dependency since the endpoint requires POST.

---

## Component wiring

### AppShell

The main layout component uses hooks to fetch data and wire up interactions:

```typescript
export default function AppShell() {
  const { data: conversations = [] } = useConversations();
  const decisionMutation = useDecision();

  const handleAction = (optionId: string, justification?: string) => {
    decisionMutation.mutate({
      conversationId: selectedId,
      optionId,
      action,
      justification: justification || '',
    });
  };
  // ...
}
```

### ScenarioPanel

The sidebar scenario panel uses `useScenarios` and `useSubmitScenario`:

```typescript
export default function ScenarioPanel() {
  const { data: scenarios = [] } = useScenarios();
  const submitMutation = useSubmitScenario();

  return (
    <div>
      {scenarios.map(s => (
        <button onClick={() => submitMutation.mutate(s.name)}>
          {s.title}
        </button>
      ))}
    </div>
  );
}
```

### ActionBar

The action bar receives `isPending` from the decision mutation to show loading state:

```typescript
<ActionBar
  options={conversation.actionRequired.options}
  isActioned={isActioned}
  onAction={handleAction}
  isPending={decisionMutation.isPending}
/>
```
