# Clients and deployment

## Calling an agent through Kong

### curl

```bash
GW=https://<proxy-url>/pet-agent
H=(-H 'Content-Type: application/json')   # add -H "apikey: $KEY" if protected

curl -s "${H[@]}" $GW/.well-known/agent-card.json | jq '{name, url}'

curl -s -X POST $GW/ "${H[@]}" -d '{
  "jsonrpc":"2.0","id":"1","method":"message/send",
  "params":{"message":{"kind":"message","messageId":"m-1","role":"user",
    "parts":[{"kind":"text","text":"How often should I walk a puppy?"}]}}}' | jq

curl -s -N -X POST $GW/ "${H[@]}" -H 'Accept: text/event-stream' -d '{
  "jsonrpc":"2.0","id":"2","method":"message/stream",
  "params":{"message":{"kind":"message","messageId":"m-2","role":"user",
    "parts":[{"kind":"text","text":"Tips for a new cat?"}]}}}'
```

Or all at once: `./scripts/a2a-smoke-test.sh $GW`.

### Python (no SDK)

```python
import json, uuid, urllib.request

GW = "https://<proxy-url>/pet-agent"
HDRS = {"Content-Type": "application/json"}   # add "apikey": "..." if protected

def a2a(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}).encode()
    req = urllib.request.Request(GW + "/", data=body, headers=HDRS, method="POST")
    return json.load(urllib.request.urlopen(req))

card = json.load(urllib.request.urlopen(urllib.request.Request(GW + "/.well-known/agent-card.json", headers=HDRS)))
print(card["name"], card["url"])

r = a2a("message/send", {"message": {"kind": "message", "messageId": str(uuid.uuid4()), "role": "user",
                                     "parts": [{"kind": "text", "text": "What should my cat eat?"}]}})
print(r["result"]["status"]["state"], r["result"]["artifacts"][0]["parts"][0]["text"])
```

### Python A2A SDK

```bash
pip install a2a-sdk
```

Point the SDK client at the card URL through Kong (`https://<proxy-url>/pet-agent/.well-known/agent-card.json`). Because Kong rewrites the card's `url`, the SDK sends all follow-up calls through the gateway. Pass auth headers through the SDK's HTTP client (an `httpx.AsyncClient(headers={"apikey": "..."})`).

### Agent calling agent

An orchestrator (LangGraph, CrewAI, Google ADK, Semantic Kernel, your own code) keeps a list of agent card URLs on the gateway, reads each card to learn skills, then sends `message/send` to the best match. One gateway credential covers all agents (example 06).

## Deploying

### 1. Run the agent somewhere Kong can reach

See [agent/README.md](../agent/README.md): local + Cloudflare tunnel / ngrok for tests, Azure Container Apps or Kubernetes for real use.

### 2a. Plugin with decK (works on Serverless gateways)

```bash
export KONNECT_TOKEN="kpat_..."   # created in the right Konnect org
FLAGS="--konnect-addr https://us.api.konghq.com --konnect-token $KONNECT_TOKEN --konnect-control-plane-name serverless-api-gateway-demo"

deck gateway diff examples/01-a2a-basic.yaml $FLAGS
deck gateway sync examples/01-a2a-basic.yaml $FLAGS
deck gateway reset $FLAGS --select-tag a2a-example-01   # remove it again
```

Every example uses its own `select_tags`, so syncing one never touches other config.

### 2b. Plugin in the Konnect UI

1. API Gateway → control plane → **Gateway services** → new, URL = agent URL, read timeout 120000.
2. **Routes** → new, path `/pet-agent`.
3. Route → **Plugins** → **AI A2A Proxy** → Logging: statistics on, payloads off → **Save**.

### 2c. Terraform

```bash
cd terraform && cp terraform.tfvars.example terraform.tfvars
export KONNECT_TOKEN="kpat_..."
terraform init && terraform validate && terraform apply
```

### 2d. AI Agent entity (AI Gateway 2.0)

UI: **Agents** → choose gateway → **New agent** → Type **A2A (Agent-to-Agent)** → URL → Route base path → Access (auth strategy, ACL) → **Create**.

kongctl:

```bash
export AI_GATEWAY_ID=<id>
kongctl apply -f examples/07-ai-agent-entity.kongctl.yaml
```

On-prem AI Gateway: convert with `deck file ai2kong`.
