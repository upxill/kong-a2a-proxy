# A2A in 5 minutes

A2A (Agent2Agent) is an open protocol for one AI agent to discover another and hand it a task. MCP connects an agent to **tools**; A2A connects an agent to **another agent**.

| | MCP | A2A |
| --- | --- | --- |
| Connects | Agent → tools / data | Agent → agent |
| Discovery | `tools/list` | Agent Card at `/.well-known/agent-card.json` |
| Unit of work | Tool call | Task (can be long-running, multi-turn) |
| State | Per call | Task lifecycle: submitted → working → completed |
| Kong's role | Can be the server (REST → tools) | Proxy in front of a real agent |

## Agent Card

```json
{
  "protocolVersion": "0.3.0",
  "name": "Pet Care Advisor",
  "description": "Answers questions about caring for pets.",
  "url": "https://<proxy>/pet-agent/",
  "preferredTransport": "JSONRPC",
  "additionalInterfaces": [
    {"url": "https://<proxy>/pet-agent/", "transport": "JSONRPC"},
    {"url": "https://<proxy>/pet-agent/v1", "transport": "HTTP+JSON"}
  ],
  "version": "1.0.0",
  "capabilities": {"streaming": true, "pushNotifications": false},
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [{"id": "pet-care-advice", "name": "Pet care advice", "description": "...", "tags": ["pets"]}]
}
```

## Sending a task (JSON-RPC)

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "messageId": "m-1",
      "role": "user",
      "parts": [{"kind": "text", "text": "How often should I walk a puppy?"}]
    }
  }
}
```

Response (a Task):

```json
{
  "jsonrpc": "2.0", "id": "1",
  "result": {
    "kind": "task",
    "id": "c45e7ced-...",
    "contextId": "9f0e...",
    "status": {"state": "completed", "timestamp": "2026-11-11T03:40:00Z"},
    "artifacts": [{"artifactId": "a1", "name": "answer",
                   "parts": [{"kind": "text", "text": "Puppies do best with several short walks a day..."}]}],
    "history": [ ... ]
  }
}
```

Send a follow-up in the same conversation by setting `params.message.contextId` (and `taskId` to continue a task that is `input-required`).

## Methods

| Method | Purpose |
| --- | --- |
| `message/send` | Send a message; returns a Task or a Message |
| `message/stream` | Same, streamed as SSE events |
| `tasks/get` | Get a task's current state |
| `tasks/list` | List tasks |
| `tasks/cancel` | Cancel a running task |
| `tasks/resubscribe` | Re-attach to a task's stream |
| `tasks/pushNotificationConfig/*` | Webhook notifications for long tasks |
| `agent/getExtendedAgentCard` | Authenticated, more detailed card |

REST binding equivalents: `POST /v1/message:send`, `POST /v1/message:stream`, `GET /v1/tasks/{id}`, `POST /v1/tasks/{id}:cancel`.

## Task states

`submitted` → `working` → `completed`, or `input-required` (agent needs more from the caller), `auth-required`, `canceled`, `failed`, `rejected`, `unknown`.

## Streaming events (`message/stream`)

Each SSE `data:` line is a JSON-RPC response whose `result` is one of:

| `kind` | Meaning |
| --- | --- |
| `task` | Initial task |
| `status-update` | State change; `final: true` on the last one |
| `artifact-update` | A chunk of output; `append`, `lastChunk` |
| `message` | A direct message reply |

## Common error codes

| Code | Meaning |
| --- | --- |
| `-32700` | Parse error |
| `-32600` | Invalid request (e.g. no JSON-RPC envelope) |
| `-32601` | Method not found |
| `-32602` | Invalid params |
| `-32001` | Task not found |
| `-32002` | Task not cancelable |
| `-32004` | Unsupported operation |
