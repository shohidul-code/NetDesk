#!/usr/bin/env bash
# Smoke test a running NetDesk API (PROPOSAL §13.1). Exits non-zero on the first failure.
#   scripts/smoke.sh http://localhost:8000
#   scripts/smoke.sh https://netdesk-api.onrender.com
# Later phases add: login (3), one chat turn (4), MCP tool list and host check (6, 9).
set -euo pipefail

BASE_URL="${1:?usage: scripts/smoke.sh <base-url>}"
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

echo "SMOKE PASSED: $BASE_URL"
