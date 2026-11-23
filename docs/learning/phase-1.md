# Phase 1 — Foundation: viva notes

## What was built and why

- `pyproject.toml` + `uv.lock` (committed): exact, reproducible installs; a 7-day cooldown skips brand-new package releases.
- Settings with pydantic-settings: secrets are `SecretStr`; the app refuses to start without `DATABASE_URL` or `JWT_SECRET_KEY` (rubric B1).
- One error envelope for every error: `{"error": {"code", "message", "details", "request_id"}}`. A 422 never echoes input; a 500 never shows a traceback (B5).
- A request ID on every response, error body and JSON log line, so a user's error report can be found in the logs.
- Async SQLAlchemy engine and a per-request session; `/api/v1/health` checks the database and returns 503 when it is down.
- Alembic with the async template; the URL comes from the settings, never from `alembic.ini`.
- A multi-stage Dockerfile that runs as a non-root user and migrates before serving; Compose with db, TEI embeddings and api (B11).
- `scripts/smoke.sh <url>`: health and `/docs`, non-zero exit on any failure.
- CI on GitHub: lint, format, types and tests against pgvector, plus a fresh-clone `docker compose up` and smoke test.
- `tests/test_rubric_rules.py`: the quiet rubric slips (`create_all`, `uv.lock`, `.env`, auth on routes, 422/500 bodies) fail CI automatically.

## Five locations to explain

- `app/core/config.py:21`: `database_url: SecretStr` with no default. A missing value raises `ValidationError` when `create_app()` builds the settings, so the app cannot start half-configured.
- `app/core/errors.py:72`: `_validation_error` keeps only the field path and message. FastAPI's default 422 includes `input`, which could leak a password.
- `app/core/logging.py:49`: `RequestIdMiddleware` is a pure ASGI middleware, not `BaseHTTPMiddleware`, so the context variable it sets is still visible to the 500 handler that runs outside it.
- `app/core/db.py:47`: `pool_pre_ping=True` checks a pooled connection before use, which matters when Neon scales to zero and drops idle connections.
- `Dockerfile:25`: `alembic upgrade head && exec uvicorn ...`. Migrations run before the server; `exec` makes uvicorn PID 1 so it receives the stop signal.

## Likely viva questions

1. **Why does the app crash on a missing secret instead of using a default?** A default secret would be the same on every deployment and anyone could forge tokens. Failing at startup is loud and safe; failing later is silent and dangerous.
2. **Why is the request ID validated?** It is copied into logs. An attacker-chosen ID with odd characters could forge log lines, so only short alphanumeric IDs are reused; anything else is replaced.
3. **How do you prove a 500 does not leak a traceback?** `tests/test_rubric_rules.py` adds a route that raises `RuntimeError("secret internal detail")` and checks the body has neither "Traceback" nor the message, but does have the envelope and a request ID.
4. **Why Alembic and not `create_all`?** Alembic records every schema change as a versioned, reviewable migration that runs the same way in tests, CI and production. `create_all` only creates missing tables and cannot change existing ones.
5. **Why is the database on host port 5433?** Port 5432 was already used by a local PostgreSQL. Inside Compose the api still talks to `db:5432`; only the host mapping differs.

## Rubric rows this phase moves (PROPOSAL §4)

- **B1 Setup:** done: uv with committed `uv.lock`, `/api/v1` prefix, `SecretStr` settings, complete `.env.example`, startup crash tested. (gitleaks arrives in Phase 8.)
- **B5 Errors:** envelope, handlers, 422 without input and 500 without traceback done; per-status tests for 201/401/403/409 come with the routes in Phases 2–3.
- **B11 Docker:** multi-stage non-root Dockerfile and Compose done; fresh-clone start passes in CI.
- **D Git:** small conventional commits, one per task.
