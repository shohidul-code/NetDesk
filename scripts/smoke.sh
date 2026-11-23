#!/usr/bin/env bash
# Smoke test a running NetDesk API (PROPOSAL §13.1). Exits non-zero on the first failure.
#   SMOKE_EMAIL=... SMOKE_PASSWORD=... scripts/smoke.sh http://localhost:8000
#   SMOKE_EMAIL=... SMOKE_PASSWORD=... scripts/smoke.sh https://netdesk-api.onrender.com
# SMOKE_EMAIL / SMOKE_PASSWORD: a seeded demo account (never printed). Login is covered;
# later phases add one chat turn (4) and the MCP tool list and host check (6, 9).
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

echo "SMOKE PASSED: $BASE_URL"
