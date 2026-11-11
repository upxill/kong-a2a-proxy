# Sample A2A agent: Pet Care Advisor

A dependency-free A2A agent for testing Kong. It implements:

| Endpoint | Binding | Notes |
| --- | --- | --- |
| `GET /.well-known/agent-card.json` (and `agent.json`) | — | Agent Card; `url` from `AGENT_PUBLIC_URL` |
| `POST /` `message/send` | JSON-RPC | Returns a completed Task with an `answer` artifact |
| `POST /` `message/stream` | JSON-RPC + SSE | Task → `working` → artifact chunks → `completed` |
| `POST /` `tasks/get` | JSON-RPC | Look up a task |
| `POST /` `tasks/cancel` | JSON-RPC | Returns "not cancelable" (tasks finish instantly) |
| `POST /v1/message:send` | REST | Subset of the REST binding |
| `GET /v1/tasks/{id}` | REST | Subset of the REST binding |
| `GET /health` | — | Health check |

Answers come from built-in tips, or from an LLM when `LLM_URL` points at an OpenAI-compatible endpoint, for example your Kong AI Proxy route in front of Azure AI Foundry.

## Run locally

```bash
python3 agent.py                                   # http://localhost:10000
../scripts/a2a-smoke-test.sh http://localhost:10000
```

With an LLM behind Kong:

```bash
LLM_URL=https://<proxy-url>/chat/completions LLM_APIKEY=<optional> python3 agent.py
```

## Docker

```bash
docker build -t pet-care-a2a .
docker run -p 10000:10000 -e AGENT_PUBLIC_URL=http://localhost:10000/ pet-care-a2a
```

## Make it reachable from a Kong Serverless gateway

Serverless gateways run in Kong's cloud, so the agent needs a public HTTPS URL:

| Option | Command |
| --- | --- |
| Cloudflare tunnel (quick test) | `cloudflared tunnel --url http://localhost:10000` → use the printed `https://*.trycloudflare.com` |
| ngrok | `ngrok http 10000` |
| Azure Container Apps | `az containerapp up --name pet-care-a2a --source . --ingress external --target-port 10000` |

Set `AGENT_PUBLIC_URL` to that public URL. Through Kong, the card's `url` is rewritten to the gateway address anyway.
