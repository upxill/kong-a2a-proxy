# Security

| Layer | Plugin path (`ai-a2a-proxy`) | Entity path (AI Agent) |
| --- | --- | --- |
| Identity | key-auth, openid-connect | `access.auth_strategies` (one) |
| Access | acl plugin (consumers, groups) | `access.acls` allow/deny + CEL |
| Abuse | rate-limiting(-advanced), request-size-limiting | AI Policies |
| To the agent | service TLS, request-transformer headers | `config.upstream.auth` SigV4, `config.certificates`, `config.ca_certificates` |

## API keys + group ACL

[examples/02-key-auth-acl.yaml](../examples/02-key-auth-acl.yaml): `key-auth` identifies the caller, `acl` with `include_consumer_groups: true` allows the `pet-apps` group. `hide_credentials: true` keeps the gateway key from reaching the agent.

## OAuth 2.0 between agents

[examples/03-oidc.yaml](../examples/03-oidc.yaml): the calling agent uses client credentials at your IdP and sends `Authorization: Bearer <token>`. Kong validates (JWT or introspection), checks `scopes_required`, and passes `sub` / `azp` to the agent as headers so it knows which agent is calling.

## Protect the Agent Card?

| Choice | Effect |
| --- | --- |
| Public card, protected tasks | Anyone can discover; only authenticated callers send tasks. Add a second route for `/.well-known` without auth, or use the extended card (`agent/getExtendedAgentCard`) for private details |
| Everything protected (examples 02–06) | Discovery needs a credential too |

## Rate and size limits

[examples/04-rate-limit-and-size.yaml](../examples/04-rate-limit-and-size.yaml). Streaming requests count once per request regardless of how many events they return.

## Upstream auth (entity)

```yaml
config:
  url: https://bedrock-agentcore.us-east-1.amazonaws.com/...
  upstream:
    auth:
      type: aws
      region: us-east-1
      assume_role_arn: arn:aws:iam::123456789012:role/agentcore-invoke
```

## Checklist

- [ ] Auth on every agent route
- [ ] ACL so only intended callers reach each agent
- [ ] Rate limits sized for the agent's real capacity
- [ ] `log_payloads: false` in production (payloads can contain personal data)
- [ ] Secrets via `${{ env "DECK_..." }}` or a vault
- [ ] `retries: 0` on the service to avoid duplicate tasks
