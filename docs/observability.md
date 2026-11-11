# Observability

Turn on `config.logging.log_statistics: true`. Add `log_payloads: true` only when debugging.

## Log fields (`ai.a2a` namespace)

Each A2A call adds an entry to `ai.a2a.rpc[]` in log plugin output (HTTP Log, File Log, OpenTelemetry logs):

| Field | Meaning |
| --- | --- |
| `method` | e.g. `message/send`, `tasks/get`, `unknown` |
| `binding` | `jsonrpc` or `rest` |
| `latency` | Upstream time (ms) |
| `id` | JSON-RPC request id |
| `task_id` | Task id from the response |
| `task_state` | `submitted`, `working`, `input-required`, `completed`, `canceled`, `failed`, `rejected`, `auth-required`, `unknown` |
| `context_id` | Conversation id |
| `error` | JSON-RPC error, if any |
| `response_body_size` | Bytes |
| `streaming` | `true` for SSE |
| `ttfb_latency` | Time to first byte for streams |
| `sse_events_count` | Number of SSE events |
| `payload.request` / `payload.response` | Bodies (only with `log_payloads`), capped at `max_payload_size` |

## OpenTelemetry

With the OpenTelemetry plugin (tracing on), Kong adds a `kong.a2a` child span:

| Attribute | Meaning |
| --- | --- |
| `kong.a2a.operation` | A2A method |
| `kong.a2a.protocol.version` | Protocol version |
| `kong.a2a.task.id` / `kong.a2a.task.state` | Task |
| `kong.a2a.context.id` | Conversation |
| `kong.a2a.streaming` / `kong.a2a.sse_events_count` | Streaming |
| `rpc.system` / `rpc.method` | JSON-RPC only |

Example: [examples/05-observability.yaml](../examples/05-observability.yaml).

## Konnect

- Control plane → **Analytics**: requests, errors, latency per route.
- Explorer / Dashboards: agentic usage analytics.

## Useful questions to answer

| Question | Use |
| --- | --- |
| Which agents are slowest? | `latency` by route |
| How many tasks fail? | `task_state = failed` count |
| Are agents asking for more input? | `task_state = input-required` |
| Who calls which agent? | consumer + route |
| Is streaming healthy? | `ttfb_latency`, `sse_events_count` |

References: [A2A metrics](https://developer.konghq.com/ai-gateway/ai-otel-metrics/#a2a-metrics), [AI A2A Proxy logs](https://developer.konghq.com/ai-gateway/ai-audit-log-reference/#ai-a2a-proxy-logs).
