# How Kong handles A2A

Kong is a **transparent, protocol-aware proxy**: requests and responses pass through unchanged (except the Agent Card URLs), while Kong understands enough of A2A to secure and observe it.

## What Kong does

| Step | Detail |
| --- | --- |
| 1. Match the route | Normal Kong routing, e.g. `/pet-agent` |
| 2. Run security plugins | key-auth / OIDC, ACL, rate limiting, size limits |
| 3. Detect A2A | JSON-RPC: a `jsonrpc` field plus a known method, or an `A2A-Version` header (unknown methods logged as `unknown`). REST: path suffix + method (`/v1/message:send` …); any prefix is ignored |
| 4. Proxy to the agent | Body unchanged |
| 5. Rewrite the Agent Card | On card responses, `url` and `additionalInterfaces[].url` become the gateway address (built from `X-Forwarded-*` when behind a load balancer) |
| 6. Stream | `text/event-stream` responses are passed through chunk by chunk |
| 7. Record telemetry | Method, binding, latency, task id/state, context id, errors, sizes, streaming stats |

## What Kong does not do

| Not done | Implication |
| --- | --- |
| Route between agents | The caller picks the agent (one route per agent) |
| Merge or aggregate responses | Orchestration belongs in your orchestrator agent |
| Store task state | The agent owns tasks; `tasks/get` goes to the same agent |
| Modify messages | No prompt guards on A2A traffic; validate in the agent |

## Detection limits

| Case | Behaviour |
| --- | --- |
| JSON-RPC body larger than `max_request_body_size` | Not parsed; still proxied (no A2A metadata recorded) |
| Unknown JSON-RPC method with `A2A-Version` header | Logged as method `unknown` |
| Non-A2A request on the route | Proxied normally |
| Logging enabled | `Accept-Encoding` removed from requests so responses can be parsed |

## Plugin vs entity

| | `ai-a2a-proxy` plugin | AI Agent entity (`type: a2a`) |
| --- | --- | --- |
| Where | Any Kong Gateway route (3.14+) | AI Gateway 2.0 → Agents |
| Route | You create Service + Route | Built in (`config.url`, `config.route`) |
| Auth | Kong auth plugins (key-auth, OIDC…) | One AI Auth Strategy (key-auth or OIDC) |
| ACL | ACL plugin (consumers/groups) | `access.acls` incl. CEL `allow_when` / `deny_when` (3.16+) |
| Upstream auth | Plugins / service config | `config.upstream.auth` (AWS SigV4), `config.certificates`, `config.ca_certificates` |
| Config | `logging.*`, `max_request_body_size` | `config.logging.*`, `config.max_request_body_size`, route, upstream |
| Managed with | UI, decK, Terraform, Admin API, KIC | UI, kongctl, AI Gateway API |
| Plain HTTP mode | n/a | `type: http` = pass-through without A2A processing |
