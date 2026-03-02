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
}
```

The top-level type representing a complete event analysis with all agent data.

---

## Backend alignment

| Frontend (TypeScript) | Backend (Python) |
|----------------------|-----------------|
| `AgentInfo` | `AgentAnalysisResponse` |
| `ActionOption` | `ActionOptionResponse` |
| `ModeratorSummaryData` | `ModeratorSynthesisResponse` |
| `Conversation` | `AnalyzeResponse` (partial) |

Field naming conventions differ by language: `camelCase` in TypeScript, `snake_case` in Python. The API response uses Python conventions; the frontend transforms as needed.
