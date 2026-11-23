# Phase 8 — Hardening and QA: viva notes

## What was done and why

- **Every row of the security matrix has a test.** `docs/SECURITY_TESTS.md` maps each
  PROPOSAL §10.2 threat to the test(s) that verify it. 17 rows were already covered; this
  phase added the rest:
  - **Oversized requests:** bodies over 64 KB get 413 in our error envelope. A declared
    `Content-Length` is refused up front; a streamed body is counted while it is read.
    FastAPI turns any body-read error into its own 400, so after an overrun the middleware
    replaces the response with our 413. `/mcp` is covered too.
  - **Sensitive logs:** every log line is redacted. Bangladeshi phone numbers (also
    URL-encoded) become `[phone]`, JWTs and Bearer tokens become `[token]`, and
    `password=`, `q=` and `token=` values become `[redacted]`. uvicorn's own access log
    used to bypass our formatter and print full URLs, so a phone typed into the
    connections search reached the logs; it now goes through the same JSON formatter.
    Checked under a real uvicorn run.
  - **Tokens:** an `alg=none` token is refused (401).
  - **Data sent to the model provider:** no tool output, for any tool or role, contains a
    phone number or an address.
- **CI security job:**
  - pip-audit (pinned) on the locked Python dependencies;
  - `npm audit` (fails on high);
  - gitleaks (pinned, checksum-verified) over the whole git history. Two synthetic test
    values are ignored by exact fingerprint, not by folder.

  Dependabot opens weekly PRs for uv, npm and Actions with the same 7-day cooldown, and
  skips TypeScript 6+ until the type tools support it.
- **Coverage: 98% line and branch, with a 95% floor in CI.** Coverage first showed some
  well-tested services at 37%: async SQLAlchemy runs code in greenlets, which coverage
  ignores unless told to. With `concurrency = ["greenlet", "thread"]` the numbers became
  real.
- **Latency** (`docs/PERFORMANCE.md`): every list endpoint is under 20 ms at p95. Chat p95
  was 22 s on the free model tier; the slowest turn was a single model call with no tool,
  so the time is the provider's, not ours.
- **P1:** `GET /chat/usage` lets the assistant show "messages left today" before the first
  message.

## Five locations to explain

- `app/core/body_limit.py`: the two checks, and why the response is swapped (FastAPI
  turns body-read errors into a 400).
- `app/core/logging.py` (`redact`, `configure_logging`): the order of the patterns (query
  values before phones), and routing uvicorn's loggers through our handler.
- `tests/test_tool_privacy.py`: what leaves our system for the model provider.
- `.github/workflows/ci.yml` (security job) and `.gitleaksignore`: pinned and verified
  tools, and why false positives are listed one by one.
- `pyproject.toml` (`[tool.coverage.run]`): `concurrency = ["greenlet", "thread"]`.

## Likely viva questions

1. **Why 64 KB?** The largest legitimate body is a 1,000-character chat message or a
   notice. A small cap protects a 512 MB server from memory abuse.
2. **Why redact in the formatter, not at each log call?** One place catches every logger:
   our own, uvicorn's, and libraries'. A forgotten call site cannot leak.
3. **Coverage is 98%. Is the code correct?** No: coverage shows what ran, not that it is
   right. The security tests assert behaviour (status codes, bodies, no leaks); coverage
   only shows where no test looks.
4. **Why is chat slow, and is it a bug?** The free model endpoint takes 1 to 22 s per call
   and sometimes retries. Our part (embedding, SQL, tools) takes milliseconds. A paid
   tier, a shorter timeout or streaming would help; all are recorded as options.
5. **What does gitleaks scan, and why the whole history?** A secret committed once and
   deleted later is still in git history and still leaked, so the job checks every commit.

## Rubric rows this phase moves (PROPOSAL §4)

- **Security and testing:** the full matrix tested, dependency and secret scanning in CI,
  98% coverage, measured performance.
