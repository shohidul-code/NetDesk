# TRD — NetDesk

Technical requirements. **Source of truth: `PROPOSAL.md`.** This file gives the short version and points to the section; it does not copy tables or defaults. Phase order and gates are in `BUILD_PLAN.md`; tables are in `SCHEMA.md`.

## 1. Stack (fixed; see CLAUDE.md)

| Layer | Choice | Reason |
|---|---|---|
| Language, packaging | Python 3.12 with uv | Lockfile committed |
| Web framework | FastAPI | Async, automatic Swagger |
| Database | PostgreSQL 16 with pgvector | One database for data and vectors |
| ORM, migrations | Async SQLAlchemy 2 with asyncpg; Alembic (async template) | Schema only through Alembic |
| Settings | pydantic-settings | Fails fast on missing secrets |
| Passwords | pwdlib[argon2] | Argon2id |
| Tokens | PyJWT | HS256, short expiry |
| LLM | `openai` SDK against Gemini's OpenAI-compatible endpoint | One client and tool format (§9.1). Which model the class used is open question 1 |
| Embeddings | TEI serving `intfloat/multilingual-e5-small`, 384 dims | Fixed model and size (§9.1) |
| MCP | Official `mcp` SDK, version pinned | HTTP at `/mcp` and stdio (§9.7) |
| Rate limits | slowapi | In memory, one instance (§10.4) |
| Tests, checks | pytest, pytest-asyncio, httpx; ruff; mypy | Commands in CLAUDE.md |
| Frontend | React, TypeScript, Vite, React Router, TanStack Query, Tailwind, shadcn/ui | Phase 7 only; types from `/openapi.json` |
| Containers | Docker, Docker Compose (api, db, embeddings) | §12.1 |
| Hosting | Render web service and static site; Neon Postgres | §12.2 |

## 2. Architecture

Diagrams: PROPOSAL §6.1 and §6.3. Layout: `app/modules/<feature>/{controllers,services,repositories,schemas,models,dependencies}.py`.

| Layer | May do | Must not do |
|---|---|---|
| Controller | HTTP only: parse, call one service, return a schema | Contain rules or queries; import repositories |
| Service | Business rules; ends writes with `await session.commit()` | Touch HTTP objects or write SQL |
| Repository | SQL only; every query takes the `Scope` | Contain rules |

- REST routes, agent tools and MCP tools call the same services (§6.4). A rule exists once.
- `get_current_user` builds the `Scope`. Out of scope → 404. Role not allowed → 403 (§7.3).

## 3. API

Base path `/api/v1`. Endpoint table, roles and errors: PROPOSAL §8.1. Public routes: `/health`, `/auth/register`, `/auth/login`, `/docs`. Every other route has an auth dependency.

- Lists take `limit` (default 20, max 100) and `offset` and return a total (§8.2).
- Separate Create, Update and Read schemas with `extra="forbid"`; no password hash in a read schema.

## 4. Errors

One envelope: `{"error": {"code", "message", "details", "request_id"}}`. Status codes: PROPOSAL §8.3.

| Status | When |
|---|---|
| 201, 204 | Created, deleted |
| 401 | Missing, invalid or expired token; failed login |
| 403 | Role may never do this |
| 404 | Not found, or outside the caller's scope |
| 409 | Unique or state conflict (duplicate code, reused TrxID, bills exist) |
| 421 | `/mcp` called with a host that is not allowed |
| 422 | Validation. `details` lists field and message; it never echoes the input |
| 429 | Rate limit or daily chat quota, with `Retry-After` |
| 500 | Unexpected. Envelope and `request_id` only, no traceback |
| 503 | LLM or embedding provider unavailable; chat kill switch |

Services translate `IntegrityError` into `ConflictError` before the response is sent. Global handlers build the envelope.

## 5. Authentication and authorization (PROPOSAL §10.2, §6.10)

- Argon2id: m=19456 KiB, t=2, p=1.
- JWT: HS256, 30-minute expiry, only `sub` in the token. Role and `is_active` are loaded from the database on every request.
- Login gives the same 401 body for an unknown email and a wrong password, and runs a dummy hash check for unknown emails.
- Register is claim-style: it links to an existing connection (§8.1).
- Role gates are a reusable dependency (`require_roles`). Scope checks live in repositories.

## 6. Assistant (PROPOSAL §9)

- Chat is stored: `chat_sessions` and `chat_messages` (audit fields: model, prompt version, tokens, latency). The server builds the prompt from the last 12 messages (§9.4).
- Limits: 1,000 characters per user message; 600 output tokens; 30-second request budget (§9.4).
- Quotas: daily caps per customer, per staff member and global; per-minute limit; `CHAT_ENABLED` kill switch (§9.8).
- Tools: 4 tools over 2 services, a set per role (§9.5). The registry re-checks the role, validates arguments with Pydantic, and returns `tool_not_available` for a wrong role. Tools are read-only. Each has a 5-second timeout and a 4 KB output cap. At most 3 tool rounds per turn.
- LLM client: 20-second timeout, 2 retries, then 503 (§9.2). `FakeLLM` for tests.

## 7. RAG (PROPOSAL §9.6, §12.3)

| Item | Requirement |
|---|---|
| Storage | `knowledge_documents` and `knowledge_chunks`, `vector(384)` |
| Prefixes | `passage: ` at ingest, `query: ` at question time |
| Retrieval | Exact cosine search, top 4, active documents, visibility by role. No vector index in P0; HNSW is P1 |
| Threshold | Distance limit from config; none under the limit → `NO_EVIDENCE` |
| Citations | Only chunks that were actually sent can become `sources` |
| Ingest | Script, SHA-256 per file, safe to re-run |
| Model check | Retrieval refuses to run if a document's `embedding_model` differs from config |
| Provider | `EMBEDDINGS_PROVIDER` = `tei`, `hf_inference` or `fake` |
| Cache | In-memory LRU of 512 query embeddings |
| Failure | Embedder down → `NO_EVIDENCE` with reason `knowledge_unavailable`; `/health` reports `embeddings: degraded`; tools keep working |

Live path, decided in Phase 5: option A is Hugging Face Inference with PRO ($9/month); option B is a self-hosted int8 build on a second Render free service. Ingest runs from the student's machine into Neon (§12.3).

## 8. MCP (PROPOSAL §9.7)

- One server, two transports: Streamable HTTP mounted at `/mcp`, and a stdio script.
- The FastAPI lifespan starts the MCP session manager.
- HTTP: staff-only JWT middleware (401 or 403). `transport_security` allowed hosts come from `MCP_ALLOWED_HOSTS`; a wrong host gets 421.
- stdio: acts as `MCP_STDIO_USER_EMAIL` (must be active staff) and logs to stderr only.
- Same services as REST and chat. 2 tools, 1 resource, 1 prompt.

## 9. Configuration (PROPOSAL §12.4)

Full list and examples: §12.4. Do not copy defaults here.

- Secrets are `SecretStr`. Startup fails if `DATABASE_URL` or `JWT_SECRET_KEY` is missing.
- Flags: `ALLOW_CUSTOMER_COMPLAINTS`, `CHAT_ENABLED`, `CHAT_DAILY_LIMIT_CUSTOMER`, `CHAT_DAILY_LIMIT_STAFF`, `CHAT_DAILY_LIMIT_GLOBAL`, `EMBEDDINGS_PROVIDER`, `MCP_ALLOWED_HOSTS`, `MCP_STDIO_USER_EMAIL`.
- `DATABASE_URL` for Neon uses `ssl=require`, not `sslmode` (asyncpg).
- `.env.example` lists every setting; `.env` is never committed.

## 10. Containers and deployment (PROPOSAL §12)

| Service | Role |
|---|---|
| db | `pgvector/pgvector:pg16`, named volume, healthcheck |
| embeddings | TEI image serving the e5 model, model cache volume |
| api | Dockerfile; waits for db and embeddings; runs `alembic upgrade head`, then uvicorn with `--proxy-headers` |

Live: Render web service (Docker) and static site, Neon Postgres. Behind Render's proxy, rate limits read the client IP from `X-Forwarded-For`. CORS allows only `CORS_ORIGINS`. Free-tier cold start: add a note next to the live link (§12.7).

## 11. Non-functional

| Area | Requirement |
|---|---|
| Security | Control matrix and named tests: PROPOSAL §10.2. Rate limits: login 5/min per IP, register 3/min per IP, chat 6/min per user. Body limit 64 KB → 413 |
| Reliability | `/health` reports `db` and `embeddings`; 503 if the DB is down. Alembic is the only schema path |
| Observability | JSON logs with request ID; no passwords, tokens or chat text; phone numbers masked |
| Data | Money `numeric(10,2)` taka; times `timestamptz` UTC, shown in Asia/Dhaka |

## 12. Testing (PROPOSAL §13)

- The database is a real pgvector container. Tests build the schema with `alembic upgrade head`. Never `create_all()`.
- Fakes: `FakeLLM` and a fake embedder, injected with `app.dependency_overrides`.
- `tests/test_rubric_rules.py` (Phase 1, see BUILD_PLAN Phase 1) enforces the rubric rules: no `create_all(`, `.env` untracked, every setting in `.env.example`, startup fails without `JWT_SECRET_KEY`, every non-public route has an auth dependency, no `input` in 422, no traceback in 500.
- Access tests (login, roles, IDOR, tool authorization) block a release.
- Test matrix: §13.1. Acceptance: §13.3. Eval: §9.9. Manual: fresh Docker start, MCP Inspector on both transports, `scripts/smoke.sh` on the live URL.
