# NetDesk — project instructions for Claude Code

Bangla-first AI support and dues desk for small ISPs in Bangladesh. Phitron final project, graded out of 100.

**Source of truth: `docs/PROPOSAL.md`.** Read the sections a task touches before writing code.
If the code and the proposal disagree, stop and ask me.

## How we work

- Build one phase at a time with `/phase <n>`, in the order of PROPOSAL §16. Never start the next phase until its gate passes and I say "go".
- Plan before code: say what exists, which files you will add or change, and which tests you will write. Then wait for "go".
- Small steps: one task → tests → checks → stop. Show a 3-line summary, the changed files and a conventional commit message (`feat:`, `fix:`, `test:`, `docs:`, `chore:`). I review the diff and commit myself.
- I must be able to explain every line in a viva. Prefer clear code over clever code. Add a docstring when the "why" is not obvious.
- Never say a check passed without running it and showing the output.
- If a library behaves differently from the proposal (for example, MCP SDK class names differ between versions), check the installed version and tell me. Don't guess.

## Stack (ask before adding anything else)

Python 3.12 with uv · FastAPI · pydantic-settings · async SQLAlchemy 2 + asyncpg · Alembic (async template) · PostgreSQL 16 + pgvector · PyJWT · pwdlib[argon2] · openai SDK against an OpenAI-compatible endpoint (Gemini) · TEI serving `intfloat/multilingual-e5-small` (384 dims) · official `mcp` SDK · slowapi · pytest, pytest-asyncio, httpx · ruff · mypy.

Frontend (phase 7 only, inside `frontend/`): React + TypeScript + Vite, React Router, TanStack Query, Tailwind + shadcn/ui, API types generated from `/openapi.json`.

Not allowed: Redis, Celery, LangChain or LlamaIndex, Kubernetes, extra services.

## Commands

- Install: `uv sync`
- Run: `uv run uvicorn app.main:app --reload`
- All checks (run before calling a step done): `uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q`
- New migration: `uv run alembic revision --autogenerate -m "<msg>"`, then read and fix it by hand. Apply: `uv run alembic upgrade head`
- Full stack: `docker compose up -d --build`
- Seed: `docker compose exec api python -m scripts.seed` · Ingest: `docker compose exec api python -m scripts.ingest`

## Architecture rules

- Modules: `app/modules/<feature>/{controllers,services,repositories,schemas,models,dependencies}.py`.
- Controllers handle HTTP only. Services hold business rules and call `await session.commit()`. Repositories hold SQL only. Controllers never import repositories.
- REST routes, agent tools and MCP tools call the same services. Never duplicate a rule.
- Every repository query takes the `Scope` built by `get_current_user`. Out of scope → 404. Role not allowed → 403.
- All routes live under `/api/v1`. Only `/health`, `/auth/register`, `/auth/login` and `/docs` are public; every other route has an auth dependency.
- Money is `numeric(10,2)` taka. Times are `timestamptz` in UTC.

## Rubric rules (tests must enforce these)

- Secrets come from pydantic-settings as `SecretStr`. Startup must fail if `DATABASE_URL` or `JWT_SECRET_KEY` is missing. Keep `.env.example` complete. Never read or commit `.env`.
- Schema changes go through Alembic only. Never call `create_all()`, not even in tests; tests run `alembic upgrade head`.
- One error envelope: `{"error": {"code", "message", "details", "request_id"}}`. A 422 never echoes submitted input. A 500 never shows a traceback.
- Status codes follow PROPOSAL §8.3: 201, 204, 401, 403, 404, 409, 422, 429, 503.
- Login returns the same 401 body for an unknown email and a wrong password, and runs a dummy hash check for unknown emails.
- Argon2id: memory 19456 KiB, time cost 2, parallelism 1. JWT: HS256, 30-minute expiry, token holds only `sub`; role and `is_active` are loaded from the DB on every request.
- The LLM never decides access: a tool set per role, the registry re-checks the role, arguments are validated with Pydantic, tools are read-only, at most 3 tool rounds.
- RAG: E5 prefixes `query: ` and `passage: `; the distance threshold comes from config; a NO_EVIDENCE path; only cite chunks that were actually sent.
- MCP: same services; staff-only JWT on `/mcp`; `transport_security` allowed hosts from env; the stdio server logs to stderr only.
- Seed and test data are synthetic. No real names, phone numbers or addresses.

## Don'ts

- Don't touch `frontend/` before phase 7, or backend code during phase 7 unless I ask.
- Don't weaken, skip or `xfail` tests to get to green.
- Don't add a dependency without telling me why.
- The README has an AI-assistance section; keep it accurate.
