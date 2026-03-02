---
title: Introduction
---

SwarmOps is a multi-agent AI commentary system for fintech operations. Business events trigger parallel analysis by three domain-specific AI agents, and a moderator synthesizes their output into actionable recommendations. {% .lead %}

{% quick-links %}

{% quick-link title="Quick start" icon="installation" href="/docs/quick-start" description="Get SwarmOps running locally with Docker Compose in under five minutes." /%}

{% quick-link title="Architecture" icon="presets" href="/docs/system-overview" description="Understand the event-to-action pipeline: agents, moderator, and RM queue." /%}

{% quick-link title="Agent system" icon="plugins" href="/docs/agent-compliance" description="Explore the three domain agents: Compliance, Security, and Engineering." /%}

{% quick-link title="API reference" icon="theming" href="/docs/api-analyze" description="Send events to the analyze endpoints and receive structured agent commentary." /%}

{% /quick-links %}

---

## How it works

A business event — a wire transfer, a security alert, a compliance review — enters the system and is analyzed in parallel by three domain-specific agents:

1. **Compliance Agent** — AML/KYC/sanctions analysis, regulatory triggers, jurisdictional risk
2. **Security Agent** — Threat detection, fraud indicators, authentication chain analysis
3. **Engineering Agent** — API integrity, SDK health, metadata validation, rate limits

The agents run simultaneously via LangGraph's fan-out/fan-in topology. A **Moderator** then synthesizes their analyses into a structured summary with consensus, dissent, risk assessment, and 2-4 concrete action items.

The final output is routed to a **Relationship Manager (RM)** queue. The RM makes all decisions — agents never act autonomously.

```shell
Event → prepare → ┌─ Compliance ─┐
                   ├─ Security   ─┤ → Moderator → RM Queue
                   └─ Engineering ┘
```

---

## Core principles

- **Human-in-the-loop** — Agents advise, humans decide. Every action requires RM approval.
- **Parallel analysis** — Three agents run simultaneously for speed and diverse perspectives.
- **Structured output** — All agent and moderator output follows strict Pydantic schemas.
- **Client memory** — Agents read per-client context to distinguish established patterns from anomalies.
- **Transparent dissent** — When agents disagree, the moderator surfaces both sides.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11 |
| Agent Orchestration | LangGraph (StateGraph fan-out/fan-in) |
| LLM | AWS Bedrock (Claude Haiku 4.5 default) |
| Database | PostgreSQL + pgvector |
| Cache + Pub/Sub | Redis |
| Frontend | React + TypeScript + TailwindCSS |
| Infra | Docker Compose (local), AWS ECS Fargate (prod) |

---

## Current status

SwarmOps is under active development. What's built:

- FastAPI app with CORS, health check, analyze endpoints, queue endpoints, and conversation history endpoints
- LangGraph orchestrator with parallel fan-out/fan-in
- Three domain agents with structured Pydantic output
- Moderator synthesis with action items
- SSE streaming for real-time agent updates
- Event queue with 4 pre-built scenarios — submit by name, results auto-persist
- Conversation history — in-memory store with list/get/clear endpoints; response shape matches frontend TypeScript types (camelCase JSON)
- Docker setup with nginx reverse proxy
- Frontend UI scaffold with Tailwind CSS

See the [development guide](/docs/development) for the full build roadmap, the [event queue](/docs/event-queue) to quickly trigger agent analysis, or the [Conversations API](/docs/api-conversations) to review persisted results.
