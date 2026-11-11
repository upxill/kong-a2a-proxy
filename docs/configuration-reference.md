# Configuration reference

## `ai-a2a-proxy` plugin (live schema, Kong Gateway 3.16.0.1)

Source: `GET /v2/control-planes/{id}/core-entities/schemas/plugins/ai-a2a-proxy`. **R** = required.

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `route` / `service` | foreign | — | Where it runs (route recommended) |
| `consumer` / `consumer_group` | foreign | — | In the schema; scope by route instead |
| `protocols` | set **R** | `[grpc, grpcs, http, https]` | Protocols |
| `config.logging` | record **R** | — | Logging settings |
| `config.logging.log_statistics` | boolean **R** | `false` | Add A2A metrics to log plugin output |
| `config.logging.log_payloads` | boolean **R** | `false` | Log request/response bodies. **Requires `log_statistics: true`** |
| `config.logging.max_payload_size` | integer **R** | `1048576` | Max bytes kept per logged payload; must be > 0; larger payloads are truncated |
| `config.max_request_body_size` | integer | `1048576` | Max request body parsed for A2A metadata; `0` = unlimited. Larger bodies are proxied without detection |

The schema also has a custom entity check on `config` (Kong validates combinations, e.g. payload logging needs statistics).

Minimal config:

```yaml
plugins:
  - name: ai-a2a-proxy
    config:
      logging:
        log_statistics: true
        log_payloads: false
        max_payload_size: 1048576
```

Get the schema yourself:

```bash
curl -s -H "Authorization: Bearer $KONNECT_TOKEN" \
  https://us.api.konghq.com/v2/control-planes/<cp-id>/core-entities/schemas/plugins/ai-a2a-proxy | jq
```

## AI Agent entity (AI Gateway 2.0)

From Kong's entity docs (not a live schema). API: `/v1/ai-gateways/{aiGatewayId}/agents`.

| Field | Meaning |
| --- | --- |
| `name`, `display_name` | Identifier and label |
| `type` | `a2a` (protocol-aware) or `http` (plain pass-through) |
| `enabled` | On/off |
| `ai_gateway` | Parent AI Gateway |
| `config.url` | Upstream agent URL |
| `config.route.paths` / `methods` / `protocols` / `strip_path` | Gateway route for the agent |
| `config.max_request_body_size` | Max body parsed for A2A metadata |
| `config.logging.payloads` | Log bodies |
| `config.logging.max_payload_size` | Max logged payload bytes |
| `config.logging.log_statistics` (also documented as `statistics`) | Metrics in logs; confirm the key in your Konnect |
| `config.upstream.auth.type: aws` | SigV4 to the agent: `region`, `access_key_id`, `secret_access_key`, `session_token`, `assume_role_arn`, `role_session_name`, `sts_endpoint_url` (secrets write-only, vault-referenceable) |
| `config.certificates` | One AI Certificate for mTLS to the agent (needs `https` URL) |
| `config.ca_certificates` | AI CA Certificates for a private CA (needs `https` URL) |
| `access.auth_strategies` | Up to one AI Auth Strategy (`key-auth` or `openid-connect`) |
| `access.acls.allow` / `deny` | AI Consumer, AI Consumer Group or Authenticated Group names |
| `access.acls.allow_when` / `deny_when` | CEL expressions, 1–1024 chars, Kong 3.16+ data planes |
| `policies` | AI Policy names/ids (auth policies not allowed here) |

Example: [examples/07-ai-agent-entity.kongctl.yaml](../examples/07-ai-agent-entity.kongctl.yaml).

## Useful service settings for agents

| Setting | Why |
| --- | --- |
| `read_timeout: 120000` (or more) | Agents can take time; streams stay open |
| `write_timeout`, `connect_timeout` | As needed |
| `retries: 0` for `message/send` routes | Avoid sending a task twice |
