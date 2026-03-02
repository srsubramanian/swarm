---
title: Schemas
---

SwarmOps uses Pydantic models on the backend and TypeScript interfaces on the frontend. Both are aligned so the API contract is consistent. {% .lead %}

---

## Backend schemas (Pydantic)

### AgentAnalysis

Structured output from each domain agent. Defined in `backend/app/agents/schemas.py`:

```python
class AgentAnalysis(BaseModel):
    agent_role: str       # "compliance" | "security" | "engineering"
    position: str         # One-sentence position statement
    analysis: str         # Detailed markdown analysis
    risk_level: str       # "critical" | "high" | "medium" | "low"
    confidence: str       # "high" | "medium" | "low"
    key_findings: list[str]     # 2-5 key findings
    recommended_action: str     # Specific next step
```

### ActionItem

A concrete action the RM can take:

```python
class ActionItem(BaseModel):
    label: str      # "Hold Transfer", "Approve with Conditions"
    variant: str    # "primary" (recommended) | "secondary" | "danger"
    rationale: str  # One-sentence reason
```

### ModeratorSynthesis

Output from the moderator node:

```python
class ModeratorSynthesis(BaseModel):
    status: str              # "HOLD RECOMMENDED", "CLEAR", etc.
    consensus: str           # Where agents agree
    dissent: str             # Where agents disagree (or "None")
    risk_level: str          # Overall risk level
    risk_assessment: str     # Brief justification
    key_decisions: list[str] # 1-3 most important findings
    next_steps: list[str]    # Concrete next steps
    action_items: list[ActionItem]  # 2-4 actions for RM
```

### LLM output coercion

LLMs sometimes return bullet-point strings instead of JSON arrays. A shared validator handles this:

```python
def _coerce_to_list(v: object) -> list[str]:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        lines = re.split(r"\n(?:[•\-\*]\s*|\d+\.\s*)", v)
        first = re.sub(r"^[•\-\*]\s*", "", lines[0])
        return [l.strip() for l in [first, *lines[1:]] if l.strip()]
    return [str(v)]
```

This is applied via `@field_validator` on `key_findings`, `key_decisions`, and `next_steps`.

---

## API request/response schemas

Defined in `backend/app/schemas/events.py`:

### AnalyzeRequest

```python
class AnalyzeRequest(BaseModel):
    event_type: str              # "wire_transfer", "velocity_alert", etc.
    title: str                   # Human-readable event title
    client_name: str             # Client name
    event_data: dict[str, Any]   # Arbitrary event payload
    client_memory: str = ""      # Client memory markdown (optional)
```

### AnalyzeResponse

```python
class AnalyzeResponse(BaseModel):
    agents: list[AgentAnalysisResponse]
    moderator_summary: ModeratorSynthesisResponse
```

### AgentAnalysisResponse

```python
class AgentAnalysisResponse(BaseModel):
    agent_role: str
    agent_name: str     # "Compliance Analyst", "Security Analyst", "Platform Engineer"
    position: str
    analysis: str
    risk_level: str
    confidence: str
    key_findings: list[str]
    recommended_action: str
```

### ModeratorSynthesisResponse

```python
class ModeratorSynthesisResponse(BaseModel):
    status: str
    consensus: str
    dissent: str
    risk_level: str
    risk_assessment: str
    key_decisions: list[str]
    next_steps: list[str]
    action_items: list[ActionOptionResponse]
```

---

## Frontend types (TypeScript)

Defined in `frontend/src/types/index.ts`:

```typescript
type RiskLevel = 'critical' | 'high' | 'medium' | 'low';
type AgentRole = 'compliance' | 'security' | 'engineering';
type ConversationStatus = 'live' | 'awaiting_decision' | 'concluded';

interface AgentInfo {
  role: AgentRole;
  name: string;
  status: 'analyzing' | 'complete';
  position: string;
}

interface Message {
  id: string;
  agentRole: AgentRole | 'moderator';
  agentName: string;
  content: string;
  timestamp: string;
}

interface ActionOption {
  id: string;
  label: string;
  variant: 'primary' | 'secondary' | 'danger';
}

interface ModeratorSummaryData {
  status: string;
  consensus: string;
  keyDecisions: string[];
  riskAssessment: string;
  nextSteps: string[];
}

interface Conversation {
  id: string;
  title: string;
  clientName: string;
  riskLevel: RiskLevel;
  status: ConversationStatus;
  eventType: string;
  agents: AgentInfo[];
  messages: Message[];
  moderatorSummary: ModeratorSummaryData;
  actionRequired: ActionRequired;
  clientMemory: ClientMemory;
}
```

---

## Schema alignment

The backend `AgentAnalysisResponse` maps to the frontend `AgentInfo` + `Message` content. The backend `ModeratorSynthesisResponse` maps to the frontend `ModeratorSummaryData`. Field naming follows each language's conventions — `snake_case` in Python, `camelCase` in TypeScript.
