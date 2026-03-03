---
title: Type system
---

The frontend TypeScript types mirror the backend Pydantic models, ensuring type safety across the API boundary. {% .lead %}

---

## Core types

Defined in `frontend/src/types/index.ts`:

### Enums

```typescript
type RiskLevel = 'critical' | 'high' | 'medium' | 'low';
type AgentRole = 'compliance' | 'security' | 'engineering';
type ConversationStatus = 'live' | 'awaiting_decision' | 'concluded';
type ViewMode = 'full' | 'summary';
```

### AgentInfo

```typescript
interface AgentInfo {
  role: AgentRole;
  name: string;
  status: 'analyzing' | 'complete';
  position: string;
}
```

Represents an agent's current state in a conversation. The `status` field drives UI indicators (spinner for analyzing, checkmark for complete).

### Message

```typescript
interface Message {
  id: string;
  agentRole: AgentRole | 'moderator';
  agentName: string;
  content: string;
  timestamp: string;
}
```

A single analysis message in the conversation timeline. The `agentRole` includes `'moderator'` for synthesis messages.

### ActionOption

```typescript
interface ActionOption {
  id: string;
  label: string;
  variant: 'primary' | 'secondary' | 'danger';
}
```

Maps to the backend `ActionItem`. The `variant` determines button styling in the RM action queue.

### ActionRequired

```typescript
interface ActionRequired {
  status: 'pending' | 'actioned';
  options: ActionOption[];
  actionedOption?: string;
}
```

Tracks whether the RM has taken action on a conversation.

### ClientMemory

```typescript
interface ClientMemory {
  clientName: string;
  content: string;
  lastUpdated: string;
}
```

Per-client context displayed in the memory panel.

### ModeratorSummaryData

```typescript
interface ModeratorSummaryData {
  status: string;
  consensus: string;
  keyDecisions: string[];
  riskAssessment: string;
  nextSteps: string[];
}
```

The moderator's synthesis displayed in the conversation view.

### Conversation

```typescript
interface Conversation {
  id: string;
  title: string;
  clientName: string;
  riskLevel: RiskLevel;
  status: ConversationStatus;
  eventType: string;
  startedAt: string;
  messageCount: number;
  agents: AgentInfo[];
  messages: Message[];
  moderatorSummary: ModeratorSummaryData;
  actionRequired: ActionRequired;
  clientMemory: ClientMemory;
  decision?: DecisionRecord | null;
}
```

The top-level type representing a complete event analysis with all agent data. The `decision` field is populated after an RM submits a decision.

### DecisionPayload

```typescript
interface DecisionPayload {
  conversationId: string;
  optionId: string;
  action: string;
  justification: string;
}
```

Used by the `useDecision` mutation to submit RM decisions. The hook converts `optionId` to `option_id` (snake_case) for the backend.

### DecisionRecord

```typescript
interface DecisionRecord {
  optionId: string;
  action: string;
  justification: string;
  decidedAt: string;
}
```

Returned by the backend after a decision is recorded. Maps to `ConversationRecord.decision`.

### Scenario

```typescript
interface Scenario {
  name: string;
  title: string;
  client_name: string;
  event_type: string;
}
```

Scenario metadata from `GET /api/queue/scenarios`. Used by the `ScenarioPanel` component.

### SSEEvent

```typescript
interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}
```

Parsed SSE event from streaming endpoints.

---

## Backend alignment

| Frontend (TypeScript) | Backend (Python) |
|----------------------|-----------------|
| `AgentInfo` | `AgentInfoRecord` |
| `ActionOption` | `ActionOptionRecord` |
| `ActionRequired` | `ActionRequiredRecord` |
| `ModeratorSummaryData` | `ModeratorSummaryRecord` |
| `ClientMemory` | `ClientMemoryRecord` |
| `DecisionRecord` | `DecisionRecord` |
| `Conversation` | `ConversationRecord` |

The backend uses Pydantic's `alias_generator=to_camel` to serialize `snake_case` Python fields as `camelCase` JSON, matching the frontend TypeScript types 1:1. No client-side transformation is needed.
