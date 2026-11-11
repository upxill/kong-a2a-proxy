# Architecture

## 1. Big picture

```mermaid
flowchart LR
    subgraph callers["Callers"]
      orch["Orchestrator agent"]
      app["Apps / UIs"]
    end
    subgraph konnect["Kong Konnect (SaaS)"]
      cp["Control plane<br/>Services, Routes, Plugins,<br/>Consumers, AI Agents"]
      an["Analytics / Explorer"]
    end
    subgraph dp["Kong data plane (Serverless / Dedicated / self-hosted)"]
      direction TB
      auth["Auth<br/>key-auth / OIDC"] --> acl["ACL, rate limits,<br/>size limits"] --> a2a["AI A2A Proxy<br/>detect A2A, rewrite card,<br/>pass SSE, telemetry"]
    end
    subgraph agents["A2A agents (any framework)"]
      a1["Agent A"]
      a2["Agent B"]
      a3["Bedrock AgentCore<br/>(SigV4)"]
    end
    ops["You: UI, decK,<br/>Terraform, kongctl"] --> cp
    cp == "config push (mTLS)" ==> dp
    dp -. "metrics, logs, spans" .-> an
    callers -- "A2A over HTTPS<br/>JSON-RPC, REST, SSE" --> auth
    a2a --> a1 & a2 & a3
```

| Layer | Component | Responsibility |
| --- | --- | --- |
| Callers | Orchestrator agents, apps | Discover agents (card), send tasks |
| Management | Konnect control plane | Config; never sees A2A traffic |
| Runtime | Kong data plane | Serves the proxy URL, runs plugins |
| A2A | AI A2A Proxy / AI Agent entity | Detection, card rewriting, streaming, telemetry |
| Security | key-auth / OIDC, ACL, rate limiting | Who may call which agent, how often |
| Backends | A2A agents | Do the work, own task state |

## 2. Discovery: Agent Card rewriting

```mermaid
sequenceDiagram
    participant C as Caller
    participant K as Kong /pet-agent
    participant A as Agent (private URL)

    C->>K: GET /pet-agent/.well-known/agent-card.json
    K->>A: GET /.well-known/agent-card.json
    A-->>K: {"url": "https://agent.internal:10000/", ...}
    K->>K: rewrite url + additionalInterfaces[].url<br/>to the gateway (X-Forwarded-* aware)
    K-->>C: {"url": "https://<proxy>/pet-agent/", ...}
    Note over C,K: every later call goes through Kong
```

Without the rewrite, a caller would read the agent's real address from the card and bypass the gateway.

## 3. A task: message/send

```mermaid
sequenceDiagram
    autonumber
    participant C as Caller agent
    participant K as Kong (auth, ACL, A2A proxy)
    participant A as A2A agent

    C->>K: POST /pet-agent/  jsonrpc message/send<br/>apikey / Bearer
    K->>K: authenticate, ACL, rate limit
    K->>K: detect A2A: method=message/send, binding=jsonrpc
    K->>A: POST /  (same body)
    A-->>K: result: Task {id, contextId, status: completed, artifacts}
    K->>K: record ai.a2a.rpc[]: latency, task_id, task_state
    K-->>C: same response
    C->>K: tasks/get {id}
    K->>A: tasks/get
    A-->>C: Task (via Kong)
```

## 4. Streaming: message/stream

```mermaid
sequenceDiagram
    participant C as Caller
    participant K as Kong
    participant A as Agent
    C->>K: message/stream
    K->>A: message/stream
    A-->>K: SSE: Task (submitted)
    K-->>C: forwarded immediately
    A-->>K: SSE: status-update (working)
    K-->>C: forwarded
    A-->>K: SSE: artifact-update chunks
    K-->>C: forwarded chunk by chunk (no buffering)
    A-->>K: SSE: status-update (completed, final)
    K-->>C: forwarded
    K->>K: log streaming=true, sse_events_count, ttfb_latency
```

## 5. Multi-agent behind one gateway

```mermaid
flowchart LR
    user["User"] --> orch["Orchestrator agent"]
    orch -- "1. read cards" --> k
    subgraph k["Kong gateway"]
      r1["/agents/pet-care"]
      r2["/agents/vet-booking"]
      r3["/agents/shop"]
    end
    orch -- "2. delegate tasks" --> k
    r1 --> p["Pet Care agent"]
    r2 --> v["Vet Booking agent"]
    r3 --> s["Shop agent"]
```

Each route has its own policies; the orchestrator holds one gateway credential instead of one per agent.

## 6. Models, tools and agents on one gateway

```mermaid
flowchart LR
    orch["Orchestrator agent"] --> kong
    subgraph kong["Kong data plane"]
      llm["AI Proxy<br/>/chat/completions"]
      mcp["AI MCP Proxy<br/>/petstore"]
      a2a["AI A2A Proxy<br/>/pet-agent"]
    end
    llm --> azure["Azure AI Foundry<br/>gpt-5.4-mini"]
    mcp --> api["Petstore REST API"]
    a2a --> agent["Pet Care agent"]
    agent -. "its own LLM calls<br/>(LLM_URL)" .-> llm
```

| Traffic | Plugin | Typical use |
| --- | --- | --- |
| LLM | AI Proxy | The orchestrator thinks |
| MCP | AI MCP Proxy | The orchestrator uses tools |
| A2A | AI A2A Proxy | The orchestrator delegates whole tasks to other agents |

## 7. Deployment

```mermaid
flowchart LR
    git["Git repo<br/>examples/, terraform/"] --> ci["CI / laptop"]
    ci -- "deck gateway sync<br/>(select_tags)" --> cp["Konnect control plane"]
    ci -- "terraform apply" --> cp
    ci -- "kongctl apply<br/>(AI Agent entity)" --> aigw["AI Gateway 2.0"]
    cp == push ==> dp["Data plane"]
    aigw == push ==> dp2["AI Gateway data plane"]
    agentimg["agent/ Docker image"] --> host["Container Apps / ECS / K8s<br/>(public HTTPS URL)"]
    dp --> host
    dp2 --> host
```

## 8. Security layers

```mermaid
flowchart TB
    req["A2A request"] --> l1{"1. Identity<br/>key-auth / OIDC"}
    l1 -- fail --> e401["401"]
    l1 -- ok --> l2{"2. ACL<br/>consumer / group / CEL"}
    l2 -- deny --> e403["403"]
    l2 -- allow --> l3{"3. Rate + size limits"}
    l3 -- over --> e429["429 / 413"]
    l3 -- ok --> l4["4. AI A2A Proxy<br/>telemetry"]
    l4 --> l5["5. Upstream auth<br/>SigV4 / mTLS / private CA"]
    l5 --> agent["Agent"]
```

## PNG versions

See [images/](images/) for rendered copies of every diagram.
