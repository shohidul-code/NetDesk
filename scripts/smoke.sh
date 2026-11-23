#!/usr/bin/env bash
# Smoke test a running NetDesk API (PROPOSAL §13.1). Exits non-zero on the first failure.
#   SMOKE_EMAIL=... SMOKE_PASSWORD=... scripts/smoke.sh http://localhost:8000
#   SMOKE_EMAIL=... SMOKE_PASSWORD=... scripts/smoke.sh https://netdesk-api.onrender.com
# SMOKE_EMAIL / SMOKE_PASSWORD: a seeded STAFF demo account (never printed); the MCP step
# needs staff. SMOKE_CHAT=1 adds a real-model chat turn.
set -euo pipefail

BASE_URL="${1:?usage: scripts/smoke.sh <base-url>}"
: "${SMOKE_EMAIL:?set SMOKE_EMAIL (a seeded demo account) to run the login step}"
: "${SMOKE_PASSWORD:?set SMOKE_PASSWORD to run the login step}"
BASE_URL="${BASE_URL%/}"
BODY="$(mktemp)"
trap 'rm -f "$BODY"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

# GET a path and check the status code. --max-time 90 covers a Render cold start.
expect_status() {
  local path="$1" expected="$2" code
  code="$(curl -sS -o "$BODY" -w '%{http_code}' --max-time 90 "$BASE_URL$path")" \
    || fail "$path: no response from $BASE_URL"
  [ "$code" = "$expected" ] || fail "$path returned $code, expected $expected: $(head -c 300 "$BODY")"
  echo "ok: $path -> $code"
}

# 1. Health first: if this fails, nothing else will work.
expect_status /api/v1/health 200
grep -q '"db":"ok"' "$BODY" || fail "/api/v1/health did not report db ok: $(cat "$BODY")"

# 2. Swagger is the public API page examiners open.
expect_status /docs 200

# 3. Log in with the OAuth2 form, then use the token. Neither secret is ever echoed.
code="$(curl -sS -o "$BODY" -w '%{http_code}' --max-time 90 \
  --data-urlencode "username=$SMOKE_EMAIL" --data-urlencode "password=$SMOKE_PASSWORD" \
  "$BASE_URL/api/v1/auth/login")" || fail "login: no response from $BASE_URL"
[ "$code" = "200" ] || fail "login returned $code, expected 200"
TOKEN="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])' <"$BODY")" \
  || fail "login response had no access_token"
echo "ok: login -> 200"

code="$(curl -sS -o "$BODY" -w '%{http_code}' --max-time 90 \
  -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/auth/me")" \
  || fail "/api/v1/auth/me: no response from $BASE_URL"
[ "$code" = "200" ] || fail "/api/v1/auth/me returned $code, expected 200"
grep -qF "$SMOKE_EMAIL" "$BODY" || fail "/api/v1/auth/me did not return the login email"
echo "ok: /api/v1/auth/me -> 200"

# 4. One chat turn with the real model. Opt-in (SMOKE_CHAT=1): it needs an LLM key, which
#    CI does not have, and it uses one message of the account's daily quota.
if [ "${SMOKE_CHAT:-0}" = "1" ]; then
  code="$(curl -sS -o "$BODY" -w '%{http_code}' --max-time 90 -X POST \
    -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/chat/sessions")" \
    || fail "create chat: no response from $BASE_URL"
  [ "$code" = "201" ] || fail "create chat returned $code, expected 201"
  CHAT_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <"$BODY")"
  code="$(curl -sS -o "$BODY" -w '%{http_code}' --max-time 90 \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"content": "Hello, what can you help me with?"}' \
    "$BASE_URL/api/v1/chat/sessions/$CHAT_ID/messages")" \
    || fail "chat turn: no response from $BASE_URL"
  [ "$code" = "201" ] || fail "chat turn returned $code, expected 201: $(head -c 300 "$BODY")"
  python3 -c 'import json,sys; assert json.load(sys.stdin)["content"].strip()' <"$BODY" \
    || fail "chat turn returned an empty reply"
  echo "ok: chat turn -> 201"
else
  echo "skip: chat turn (set SMOKE_CHAT=1 to test the real model)"
fi

# 5. MCP: list tools over Streamable HTTP with the staff token (PROPOSAL §9.7).
MCP_LIST='{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
mcp_post() {
  curl -sS -o "$BODY" -w '%{http_code}' --max-time 90 "$@" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" -d "$MCP_LIST" "$BASE_URL/mcp"
}
code="$(mcp_post)" || fail "/mcp: no response from $BASE_URL"
[ "$code" = "200" ] || fail "/mcp tools/list returned $code, expected 200: $(head -c 300 "$BODY")"
grep -q '"lookup_customer_bills"' "$BODY" || fail "/mcp did not list lookup_customer_bills"
echo "ok: /mcp tools/list -> 200"

# 6. An unknown Host must get 421 (DNS-rebinding protection). Only checked locally: a cloud
#    host such as Render routes by Host, so a fake Host never reaches our app there.
case "$BASE_URL" in
  http://localhost:* | http://127.0.0.1:*)
    code="$(mcp_post -H "Host: evil.example")" || fail "/mcp host check: no response"
    [ "$code" = "421" ] || fail "/mcp with an unknown Host returned $code, expected 421"
    echo "ok: /mcp with an unknown Host -> 421"
    ;;
  *) echo "skip: unknown-Host check (only meaningful against localhost)" ;;
esac

echo "SMOKE PASSED: $BASE_URL"
