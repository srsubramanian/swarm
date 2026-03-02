---
title: POST /api/analyze/stream
---

The streaming endpoint delivers agent results in real-time via Server-Sent Events (SSE) as each agent completes its analysis. {% .lead %}

---

## Endpoint

```shell
POST /api/analyze/stream
Content-Type: application/json
Accept: text/event-stream
```

The request body is identical to [`POST /api/analyze`](/docs/api-analyze).

---

## SSE event flow

Events are emitted in this order:

```shell
event: start
data: {"status": "processing"}

event: agent_complete
data: {"agent_role": "engineering", "agent_name": "Platform Engineer", ...}

event: agent_complete
data: {"agent_role": "compliance", "agent_name": "Compliance Analyst", ...}

event: agent_complete
data: {"agent_role": "security", "agent_name": "Security Analyst", ...}

event: moderator_complete
data: {"status": "HOLD RECOMMENDED", "consensus": "...", ...}

event: done
data: {"status": "complete"}
```

{% callout title="Agent order varies" %}
The three `agent_complete` events arrive in whatever order the agents finish. Because agents run in parallel and make independent LLM calls, the completion order is non-deterministic.
{% /callout %}

---

## Event types

| Event | Payload | When |
|-------|---------|------|
| `start` | `{"status": "processing"}` | Immediately after request |
| `agent_complete` | `AgentAnalysisResponse` JSON | Each agent finishes (3 total) |
| `moderator_complete` | `ModeratorSynthesisResponse` JSON | After all agents, moderator synthesizes |
| `done` | `{"status": "complete"}` | Stream is finished |

---

## Implementation

The streaming is powered by LangGraph's `astream` with `stream_mode="updates"`:

```python
async def _event_generator(req: AnalyzeRequest) -> AsyncGenerator[dict, None]:
    yield {"event": "start", "data": json.dumps({"status": "processing"})}

    async for event in graph.astream(_build_input(req), stream_mode="updates"):
        for node_name, node_output in event.items():
            if node_name in ("compliance", "security", "engineering"):
                analyses = node_output.get("analyses", [])
                for analysis in analyses:
                    resp = _analysis_to_response(analysis)
                    yield {
                        "event": "agent_complete",
                        "data": resp.model_dump_json(),
                    }
            elif node_name == "moderator":
                synthesis = node_output.get("moderator_synthesis")
                if synthesis:
                    resp = _synthesis_to_response(synthesis)
                    yield {
                        "event": "moderator_complete",
                        "data": resp.model_dump_json(),
                    }

    yield {"event": "done", "data": json.dumps({"status": "complete"})}
```

The endpoint uses `sse-starlette` to wrap the async generator:

```python
@router.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest) -> EventSourceResponse:
    return EventSourceResponse(_event_generator(req))
```

---

## nginx SSE configuration

The nginx reverse proxy is configured to support SSE without buffering:

```shell
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding off;
}
```

Key settings: `proxy_buffering off` prevents nginx from holding back events, and `chunked_transfer_encoding off` ensures clean SSE delivery.

---

## Client-side consumption

A JavaScript client can consume the stream with `EventSource` or `fetch`:

```javascript
const response = await fetch('/api/analyze/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(request),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  // Parse SSE events from text
}
```
