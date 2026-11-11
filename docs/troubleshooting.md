# Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `no Route matched with those values` | Wrong proxy URL / org, or not synced | Check the control plane's Proxy URL; `deck gateway diff` |
| `502` / `503` from Kong | Agent unreachable from the data plane | Serverless gateways need a **public** agent URL (tunnel or cloud host) |
| `504` / stream cut off | Service timeout too short | Raise `read_timeout` on the service |
| Card `url` still shows the agent's own address | Plugin not on this route, or card fetched directly from the agent | Fetch the card through Kong; check the plugin is enabled on the route |
| Card URL has the wrong host/scheme | Behind a load balancer without `X-Forwarded-*` | Forward `X-Forwarded-Proto/Host/Port` |
| `-32600 Invalid Request` | Body is not a JSON-RPC envelope (e.g. `{"message": ...}`) | Wrap in `{"jsonrpc":"2.0","id":..,"method":"message/send","params":{...}}`; this comes from the agent, not Kong |
| `-32601 Method not found` | Agent doesn't implement the method | Check the agent's capabilities |
| `401` | Missing apikey / token | Send `apikey` or `Authorization: Bearer` |
| `403` | ACL: caller not allowed | Add the consumer to the allowed group |
| `429` | Rate limit | Raise limits or slow the caller |
| `413` | Body too large | Raise `request-size-limiting` |
| No A2A fields in logs | `log_statistics` off, or body > `max_request_body_size` | Turn statistics on; raise `max_request_body_size` |
| `log_payloads` rejected on save | Needs `log_statistics: true` | Enable both |
| Duplicate tasks after errors | Service retries | Set `retries: 0` |
| Entity created but unreachable | AI Gateway has no data plane | Add a data plane (AI Gateway → Data plane nodes) |

## Debug order

1. `./scripts/a2a-smoke-test.sh http://<agent-direct-url>`: does the agent work?
2. `./scripts/a2a-smoke-test.sh https://<proxy>/<path>`: does it work through Kong?
3. Compare the card `url` in both runs: it should change to the gateway.
4. Check Konnect Analytics for the route.
