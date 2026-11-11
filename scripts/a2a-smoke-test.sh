#!/usr/bin/env bash
# A2A smoke test: agent card -> message/send -> tasks/get -> message/stream
#
# Usage:
#   ./scripts/a2a-smoke-test.sh <agent-base-url> ["question"]
#
# Examples:
#   ./scripts/a2a-smoke-test.sh http://localhost:10000                      # agent directly
#   ./scripts/a2a-smoke-test.sh https://<proxy-url>/pet-agent               # through Kong
#   APIKEY=xxxx ./scripts/a2a-smoke-test.sh https://<proxy-url>/pet-agent-secure
#
# Env: APIKEY (sent as "apikey" header), BEARER (Authorization: Bearer ...)
set -euo pipefail

BASE="${1:?usage: $0 <agent-base-url> [question]}"
BASE="${BASE%/}"
Q="${2:-How often should I walk a puppy?}"

H=(-H 'Content-Type: application/json')
[[ -n "${APIKEY:-}" ]] && H+=(-H "apikey: ${APIKEY}")
[[ -n "${BEARER:-}" ]] && H+=(-H "Authorization: Bearer ${BEARER}")
command -v jq >/dev/null || { echo "jq is required (brew install jq)"; exit 1; }

echo "== 1. Agent Card  GET $BASE/.well-known/agent-card.json"
CARD=$(curl -sS -w '\n%{http_code}' "${H[@]}" "$BASE/.well-known/agent-card.json")
CODE=$(tail -1 <<<"$CARD"); CARD=$(sed '$d' <<<"$CARD")
echo "HTTP $CODE"
[[ "$CODE" == "200" ]] || { echo "$CARD"; echo "FAIL: agent card"; exit 1; }
echo "$CARD" | jq '{name, url, preferredTransport, additionalInterfaces, streaming: .capabilities.streaming, skills: [.skills[].id]}'
CARD_URL=$(echo "$CARD" | jq -r .url)
if [[ "$CARD_URL" != "$BASE"* ]]; then
  echo "NOTE: card url ($CARD_URL) does not point at $BASE. Through Kong it should be rewritten to the gateway address."
fi

MSG_ID="smoke-$(date +%s)"
SEND=$(jq -n --arg q "$Q" --arg id "$MSG_ID" \
  '{jsonrpc:"2.0", id:"1", method:"message/send",
    params:{message:{kind:"message", messageId:$id, role:"user", parts:[{kind:"text", text:$q}]}}}')

echo "== 2. message/send  \"$Q\""
RES=$(curl -sS -X POST "$BASE/" "${H[@]}" -d "$SEND")
echo "$RES" | jq -e '.result' >/dev/null || { echo "$RES"; echo "FAIL: message/send"; exit 1; }
TASK_ID=$(echo "$RES" | jq -r '.result.id')
echo "$RES" | jq -r '"task=\(.result.id) state=\(.result.status.state)\nanswer: \(.result.artifacts[0].parts[0].text // .result.parts[0].text)"'

echo "== 3. tasks/get $TASK_ID"
curl -sS -X POST "$BASE/" "${H[@]}" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":\"2\",\"method\":\"tasks/get\",\"params\":{\"id\":\"$TASK_ID\"}}" \
  | jq -r '"state=\(.result.status.state // .error.message)"'

echo "== 4. message/stream (SSE)"
STREAM=$(echo "$SEND" | jq '.method="message/stream" | .id="3" | .params.message.messageId += "-s"')
curl -sS -N -X POST "$BASE/" "${H[@]}" -H 'Accept: text/event-stream' -d "$STREAM" \
  | sed -n 's/^data: //p' \
  | jq -r '.result | if .kind=="artifact-update" then "  chunk: \(.artifact.parts[0].text)"
                     elif .kind=="status-update" then "  status: \(.status.state) final=\(.final)"
                     else "  \(.kind): \(.id // "")" end'
echo "OK"
