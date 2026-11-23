# NetDesk build plan

The working checklist for the build. **Source of truth: `docs/PROPOSAL.md` §16.** Tables, endpoints, settings and prompts live in the proposal (§7, §8, §9, §12.4); this file does not copy them, so the two cannot drift.

Items tagged **[refined]** come from the proposal's *Refined plan*. Items tagged **[audit]** come from the gaps audit of 23 Nov 2026 and are scheduled in the phase where they become due.

## How every phase runs

1. `/phase <n>`: plan, then wait for "go".
2. One task at a time: tests first → smallest change → `uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q` → small conventional commit.
3. Gate: check every "Done when" item and record PASS/FAIL with the command output.
4. Viva notes in `docs/learning/phase-<n>.md`, then a **2-minute recorded explanation** of the phase's code. [refined]

## Timeline

| Phase | Effort | Gate |
| --- | --- | --- |
| 0 Scope freeze | 0.5 d | — |
| 1 Foundation | 1.5 d | **Gate 0:** `docker compose up` serves `/docs`; CI green |
| 2 Database and domain API | 3 d | — |
| 3 Authentication and authorization | 2 d | **Gate 1:** every access test green |
| 4 LLM, tools and chat | 3 d | — |
| 5 RAG | 3 d | **Gate 2:** eval run, zero leaks |
| 6 MCP | 2 d | — |
| 7 Frontend | 4 d | — |
| 8 Hardening and QA | 2 d | — |
| 9 Deployment | 1.5 d | **Gate 3:** live smoke test passes |
| 10 Submission | 2 d | — |

About 24 working days (about 22 without P1). The frontend agent may start after Gate 1.

## Phase 0 — Scope freeze (0.5 d)

- [x] Move the planning docs into `docs/`; init git with a `.gitignore` that keeps `.env` out.
- [x] Correct the proposal's status (no code yet) and make `ChatReply.message_id` a `UUID`.
- [x] Rewrite this file to match §16.
- [x] Update PRD, TRD, SCHEMA, APP_FLOW and AGENT to the Refined plan.
- [x] Update UI, FRONTEND_AGENT_BRIEF and RULES: P0 frontend = 9 core pages. [refined]
- [x] Write `docs/HUMAN_TODO.md`.
- [x] Settle open design points in the proposal: id types, bill due date, complaint status, who creates complaints, soft chat delete, 413.
- [ ] Human: send the instructor the §4 conflicts; ask classmates which LLM and embedding model the class used; book two ISP visits.

**Done when:** the instructor question is sent, the docs agree with each other, and the P0 list is frozen.

## Phase 1 — Foundation (1.5 d)

- [x] `pyproject.toml` and `uv.lock` (committed); `app/main.py` with `/api/v1/health`.
- [x] `app/core/config.py`: pydantic-settings, secrets as `SecretStr`; startup fails without `DATABASE_URL` or `JWT_SECRET_KEY`.
- [x] Declare the flags used in later phases now, so `.env.example` is complete from day one: `ALLOW_CUSTOMER_COMPLAINTS`, `CHAT_ENABLED`, `CHAT_DAILY_LIMIT_CUSTOMER`, `CHAT_DAILY_LIMIT_STAFF`, `CHAT_DAILY_LIMIT_GLOBAL`, `EMBEDDINGS_PROVIDER` (`tei | hf_inference | fake`), `MCP_ALLOWED_HOSTS`, `MCP_STDIO_USER_EMAIL`. [audit]
- [x] `.env.example` lists every Settings field, each comment on its own line. [audit]
- [x] Error envelope and global handlers; request-ID middleware; JSON logging.
- [x] Alembic with the async template.
- [x] `Dockerfile` and `compose.yaml` (db, embeddings, api). Start the TEI image download early.
- [x] `.github/workflows/ci.yml`: ruff, mypy, pytest.
- [x] `tests/test_rubric_rules.py` [refined][audit]:
  - no `create_all(` in `app/`, `tests/`, `scripts/` or `migrations/`;
  - `uv.lock` tracked and `.env` untracked (`git ls-files`);
  - every Settings field appears in `.env.example`;
  - a missing `JWT_SECRET_KEY` fails at startup;
  - every route outside `/health`, `/auth/register`, `/auth/login` and the docs has an auth dependency;
  - 422 bodies contain no `input`; 500 bodies contain no traceback.
- [x] `scripts/smoke.sh <base-url>`: health first; exit non-zero on any failure. Extended in Phases 3, 4, 6 and 9. [audit]
- [x] README skeleton: placeholders for the three submission links, the cold-start note, known limits and the AI-assistance section. [refined][audit]

**Tests:** startup fails without a secret; health returns 200; an unknown route returns the envelope with 404; a forced error returns 500 without a traceback.
**Done when (Gate 0):** `docker compose up` serves `/docs`, and CI is green on GitHub.

## Phase 2 — Database and domain API (3 d)

- [x] Models and migration `0001_core` (ids: `int` for roles, areas and packages; `uuid` everywhere else, §7.2).
- [x] Modules: areas, packages, connections, billing, complaints, notices; filters, search `q`, limit/offset with a total.
- [x] Idempotent monthly bill generation; `due_date` is the 10th of the month after `period` (§7.2).
- [x] Complaint status rule (§7.2): only the allowed changes, any other → 409. Decide whether a status update carries a note (§11.2 shows one; §8.1 has no field). [audit]
- [x] `scripts/seed.py`: idempotent, synthetic data only.
- [x] Migration `0002_payment_trail`; payment verification by TrxID (409 on reuse).
- [x] A **stub** `get_current_user` and `require_roles` on every route now, so Phase 3 swaps the stub instead of retrofitting checks.

**Tests:** CRUD with filters; 404, 409 and 422 cases; generating a month twice; TrxID reuse; seeding twice; `alembic upgrade head` on an empty DB; `alembic check` shows no drift.
**Done when:** every endpoint in §8.1, except auth, users, chat and knowledge, matches the contract.
**Risk:** business rules leaking into controllers.

## Phase 3 — Authentication and authorization (2 d)

- [x] Argon2id (19456 KiB, time cost 2, parallelism 1); PyJWT HS256, 30-minute expiry, `sub` only.
- [x] Claim-style register; OAuth2-form login; `/auth/me`; admin user endpoints; replace the stub.
- [x] Rate-limit login and register on the forwarded IP.
- [x] Enforce `ALLOW_CUSTOMER_COMPLAINTS` in the complaints service. [refined]
- [x] `smoke.sh`: add a login step. [audit]

**Tests:** the auth row of §13.1; identical 401 bodies for unknown email and wrong password; dummy hash check; IDOR → 404; customer write → 403.
**Done when (Gate 1):** every access test passes.

## Phase 4 — LLM, tools and chat (3 d)

- [x] LLM client and `FakeLLM`; prompt v1.
- [x] Migration `0003_chat`; chat module: sessions, messages, history window, daily quotas (`CHAT_DAILY_LIMIT_*`), kill switch (`CHAT_ENABLED`); deleting a session is soft (`deleted_at`, §7.2).
- [x] Tool registry: 4 role variants over 2 services, each wrapper ≤ 20 lines; the registry re-checks the role; at most 3 tool rounds. [refined]
- [x] Usage tracking; provider failures → 503.
- [x] One parametrized authorization test covers all four tools. [refined]
- [x] `ChatReply.messages_left_today` added to §8.2 (the no-information flag moves to Phase 5). [audit]
- [x] `smoke.sh`: add one chat turn. [audit]

**Tests:** the tool-calling row of §13.1; a follow-up question uses history; the 31st message gets 429.
**Done when:** a customer gets their exact bill amount in Bangla from the real model.
**Risk:** free-tier rate limits; use `FakeLLM` day to day.

## Phase 5 — RAG (3 d)

- [x] 15 help articles (bn + en). Drafted by Claude at the owner's request; the owner reviews every line. [refined]
- [x] Migration `0004_knowledge`; embedding adapters `tei`, `hf_inference`, `fake`, chosen by `EMBEDDINGS_PROVIDER`.
- [x] Ingest script; retrieval service; evidence formatting; citation filter; NO_EVIDENCE; distance threshold from config, tuned.
- [x] In-memory LRU cache for 512 query embeddings. [refined][audit]
- [x] Embedding fallback: if the embedder is down, reply NO_EVIDENCE with reason `knowledge_unavailable` and report `embeddings: degraded` on health. [audit]
- [ ] Decide the live embedding path now (option A: HF PRO, $9/month; option B: self-hosted), not on deploy day. [refined][audit]
- [x] 20 eval cases (drafted by Claude, owner reviews); `scripts/eval_chat.py` run against real Gemini and TEI. [refined]
- [x] Language rule: English questions got Bangla replies; the server now names the reply language per turn, and the scorer checks it (20/20). [eval]
- [x] Add a no-information flag to `ChatReply` (§8.2), set when retrieval returns NO_EVIDENCE and no tool answered, so the UI can style it (§11.2). [audit]

**Tests:** the RAG row of §13.1; a cache hit skips the embedder; the fallback path.
**Done when (Gate 2):** `docs/EVAL_RESULTS.md` has real, dated numbers with zero permission leaks and zero successful injections.
**Risk:** weak Bangla recall; try `multilingual-e5-base` first.

## Phase 6 — MCP (2 d)

- [x] Server with 2 tools, 1 resource and 1 prompt; mount at `/mcp` with the lifespan.
- [x] `transport_security` with allowed hosts read from `MCP_ALLOWED_HOSTS`. [refined]
- [x] Staff-only JWT middleware; `netdesk-mcp` stdio script (acts as `MCP_STDIO_USER_EMAIL`, logs to stderr only).
- [x] Client tests over both transports (SDK client: real uvicorn and the installed stdio script).
- [x] Manual check in MCP Inspector over both transports (owner, HUMAN_TODO §5b).
- [x] One CI test starts real uvicorn and lists the MCP tools, so the lifespan is exercised. [refined][audit]
- [x] `smoke.sh`: an MCP tool-list call, and a wrong `Host` header that must get 421. [refined][audit]

**Done when:** the MCP acceptance criterion in §13.3 passes locally.
**Risk:** SDK names differ between versions (`MCPServer` or `FastMCP`); pin the version and check it.

## Phase 7 — Frontend (4 d, `frontend/` only)

- [x] Generate API types from `/openapi.json`.
- [x] The 9 P0 pages: login, claim, customer home, assistant, my complaints, technician queue, admin connections, bills, notices. [refined]
- [x] Role navigation; error mapping from the envelope; chat UI with tool and source chips.
- [x] CORS allowlist applied in the API (it was configured but never wired); frontend CI job. [phase 7]
- [x] The brief's 11 acceptance checks pass in the browser at 360px against the local API (2026-11-24).
- Packages, users, knowledge and the dashboard are P1; Swagger covers them meanwhile.

**Done when:** each role completes its main workflow in the browser against the local API.

## Phase 8 — Hardening and QA (2 d)

- [x] A test for every row of the security matrix (§10.2, mapped in `docs/SECURITY_TESTS.md`); 64 KB body limit (413); log redaction (also uvicorn's access log).
- [x] pip-audit, npm audit and gitleaks in CI; Dependabot; coverage report (98%, floor 95%).
- [x] Measure p50/p95 for chat and list endpoints (`docs/PERFORMANCE.md`).
- [x] P1: messages left today shown on page load (`GET /chat/usage`).
- [ ] Remaining eval failures: 3 cases are expectation questions (see EVAL_RESULTS); owner decides.

**Done when:** CI is green with the security tests, and the measured numbers are written down.

## Phase 9 — Deployment (1.5 d)

- [ ] Neon project; Render web service and static site from `render.yaml`; env vars (`MCP_ALLOWED_HOSTS` includes the Render host; `ssl=require`).
- [ ] Seed and ingest against Neon; run the parity test.
- [ ] Run `smoke.sh` against the live URL, including the MCP tool list and host check. [refined][audit]
- [ ] Warm Render (`/api/v1/health`) before grading; keep the cold-start note next to the live link. [refined][audit]
- [ ] Demo accounts and the pricing table in the README (prices labelled hypotheses).

**Done when (Gate 3):** the smoke test passes against the live URL from a private browser window.

## Phase 10 — Submission (2 d)

- [ ] Finish the README and fill the three link placeholders.
- [ ] Record all five flows **locally** for the video, so it does not depend on free tiers; plan two takes. [refined]
- [ ] Only sourced facts or interview notes in the README and video; everything else is labelled a hypothesis. [refined]
- [ ] Pricing: at most 3 free pilots; no profitability claim. [refined]
- [ ] Upload the video to Drive ("anyone with the link"); check all three links in a private window; warm Render first. [audit]
- [ ] Tag `v1.0.0`; case study, LinkedIn text and resume bullets with measured numbers only.

**Done when:** every box in §18 is ticked.

## Cut order

If you fall behind, cut in this order: owner dashboard metrics → CSV import → Playwright → eval growth beyond 20 cases → technician UI polish.
**Never cut:** auth and tool-authorization tests, error handling, MCP over both transports, the README quickstart.

## Refined plan → where it lands

| Refined-plan row | Scheduled in |
| --- | --- |
| Scope vs time (9 P0 pages) | Phase 0 docs, Phase 7 |
| Fragile live demo | Phase 5 (embedding path, LRU cache), Phase 9 (warm Render), Phase 10 (local recording) |
| Complaint-write conflict | Phase 0 (ask the instructor), Phase 1 (flag), Phase 3 (enforce) |
| Explaining AI-written code | Every phase (2-minute explanation, small commits); Phase 1 README AI section; Phase 5 (own articles and eval cases) |
| Quiet rubric slips | Phase 1 (`tests/test_rubric_rules.py`) |
| MCP failing live | Phase 1 (`MCP_ALLOWED_HOSTS`), Phase 6 (real-uvicorn CI test, smoke), Phase 9 (live smoke) |
| Wrong channel for customers | Phase 10 (README and video pitch: web assistant as channel one) |
| Unverified market claims | Phase 10; interviews in `HUMAN_TODO.md` |
| Single-tenant pilots lose money | Phase 10 (at most 3 free pilots) |
| Tool-wrapper complexity | Phase 4 (≤ 20-line wrappers, one parametrized test) |
