# NetDesk

A Bangla-first AI support and dues desk for small internet service providers (ISPs) in Bangladesh.
Customers ask about bills and outages in Bangla and get answers from the ISP's own records;
staff get a complaint queue and dues by area. Phitron final project.

> **Status:** Phase 1 (foundation) of the roadmap in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).
> Features below the foundation are not built yet.

## Submission links

| What | Link |
| --- | --- |
| Live API docs (Swagger) | _TODO: Render URL + `/docs` (Phase 9)_ |
| Video demonstration | _TODO: Google Drive link (Phase 10)_ |
| Source code | https://github.com/shohidul-code/NetDesk |

**Cold start:** the live API runs on Render's free tier, which sleeps after 15 minutes without
traffic. The first request can take up to a minute; after that it responds normally.

## Quickstart (local)

Needs Docker (or Podman) with Compose.

```bash
cp .env.example .env      # then set JWT_SECRET_KEY to 48+ random characters
docker compose up -d --build
scripts/smoke.sh http://localhost:8000
```

Open http://localhost:8000/docs. The first start downloads the embedding model, so allow a few minutes.

## Development

```bash
uv sync
docker compose up -d db   # PostgreSQL + pgvector on host port 5433, used by the tests
uv run uvicorn app.main:app --reload
uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q
```

Schema changes go through Alembic only: `uv run alembic upgrade head`.

## MCP (staff only)

NetDesk exposes two read-only tools (`lookup_customer_bills`, `get_area_service_status`),
one resource (`netdesk://packages/active`) and one prompt (`due_bill_reminder`) to AI
clients. They call the same services as the REST API, so the access rules are the same.

**Streamable HTTP** at `http://localhost:8000/mcp`, with a technician or admin token:

```bash
TOKEN=$(curl -s --data-urlencode username=admin@netdesk.demo \
  --data-urlencode "password=$SEED_DEMO_PASSWORD" http://localhost:8000/api/v1/auth/login \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
```

In MCP Inspector (`npx @modelcontextprotocol/inspector`), choose Streamable HTTP, enter the
URL and add the header `Authorization: Bearer <token>`. No token gives 401, a customer
token 403, and a Host not in `MCP_ALLOWED_HOSTS` gives 421.

**stdio** for a local client such as Claude Desktop. It acts as `MCP_STDIO_USER_EMAIL`
(an active staff user) and reads the database settings from `.env`:

```json
{
  "mcpServers": {
    "netdesk": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/NetDesk", "netdesk-mcp"]
    }
  }
}
```

## Architecture

FastAPI modular monolith, async SQLAlchemy 2 + asyncpg, PostgreSQL 16 + pgvector, Alembic,
an OpenAI-compatible LLM client (Gemini), TEI serving `intfloat/multilingual-e5-small`,
and an MCP server. Details: [docs/PROPOSAL.md](docs/PROPOSAL.md) §6.

## Known limits

- Single-tenant: one deployment per ISP. Multi-tenancy is planned before a 4th paying customer.
- All seed and demo data is synthetic. No real customer data.
- The free Render tier sleeps when idle (see the cold-start note above).
- Pricing and market figures are hypotheses until validated by ISP interviews.

## AI assistance

This project was built with AI assistance, as allowed by the course:

- **Planning:** the architecture proposal and planning documents in `docs/` were drafted with an AI
  assistant and reviewed and edited by me.
- **Backend:** the backend code is written in Claude Code sessions, one small task at a time, with
  tests first. I review every diff, run the checks, and must be able to explain every line.
- **Frontend (Phase 7):** a coding agent builds `frontend/` only, following
  [docs/RULES.md](docs/RULES.md) and [docs/FRONTEND_AGENT_BRIEF.md](docs/FRONTEND_AGENT_BRIEF.md).
- **Help articles and evaluation cases (Phase 5):** drafted by Claude at my request from the
  synthetic demo data, then reviewed by me line by line. The first eval run is kept in
  [docs/EVAL_RESULTS_v1.md](docs/EVAL_RESULTS_v1.md).

## License

TODO: MIT (Phase 10).
