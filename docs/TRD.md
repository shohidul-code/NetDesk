# TRD — NetDesk

Technical requirements. Build order and the rubric checklist are in `BUILD_PLAN.md`; tables are in `SCHEMA.md`; assistant behaviour is in `AGENT.md`.

## 1. Stack

| Layer | Choice | Reason |
|---|---|---|
| Language and packaging | Python, managed with uv | Required; lockfile committed |
| Web framework | FastAPI | Required; async, automatic Swagger |
| Database | PostgreSQL with the pgvector extension | Required; one database for data and vectors |
| ORM and migrations | SQLAlchemy (async) with asyncpg; Alembic | Required |
| Settings | pydantic-settings | Required; fails fast on missing secrets |
| Passwords | argon2 | Required (argon2 or bcrypt) |
| Tokens | JWT with expiry | Required |
| LLM | The provider used in class, behind `app/integrations/llm/` | Swappable |
| Embeddings | The embedding server used in class, behind `app/integrations/embeddings/` | Swappable; vector size is a setting |
| MCP | Official MCP Python SDK | HTTP at `/mcp` and stdio |
| Frontend | React, Vite, TypeScript, Tailwind | Static build |
| Containers | Docker and docker-compose | Required |
| Hosting | Render: web service, Postgres, static site | Required for the live link |

## 2. Architecture

```
Frontend ──HTTPS+JWT──► FastAPI (/api/v1) ──► services ──► repositories ──► Postgres + pgvector
MCP client ──/mcp or stdio──► MCP server ──┘        │
                                                    ├──► LLM integration ──► LLM API
                                                    └──► embeddings integration ──► embedding service
```

Layer rules:

| Layer | May do | Must not do |
|---|---|---|
| Controller | Parse request, call one service, return a schema, set status code | Contain logic or queries |
| Service | Business rules, permission checks on ownership, orchestration | Touch HTTP objects or write SQL |
| Repository | All queries for one model | Contain business rules |
| Integration | Talk to one outside system | Know about HTTP routes or the database |
| MCP server / chat tools | Call services | Reimplement logic |

Dependencies are injected with `Depends`: database session, current user, role check, repositories into services, services into controllers.

## 3. Modules

`auth`, `users`, `packages`, `connections`, `bills`, `complaints`, `knowledge`, `chat`. Each folder under `app/modules/` holds `controllers`, `services`, `repositories`, `schemas`, `models`, `dependencies`.

## 4. API

Base path `/api/v1`. Full table with roles and status codes: `BUILD_PLAN.md` section 5.

Conventions:

- Plural nouns, numeric ids in the path.
- Create returns 201 with the new object; delete returns 204.
- List endpoints accept `limit` and `offset`, plus their filters, and return items with a total count.
- Partial updates use PATCH with only the changed fields.
- Request and response bodies are separate Pydantic schemas (create, update, read). Password hashes never appear in a read schema.
- Every endpoint has a summary, a response model and listed error responses so Swagger is self-explanatory.

## 5. Errors

| Error class | Status | When |
|---|---|---|
| NotFound | 404 | Id does not exist, or exists but is not the caller's to see |
| Conflict | 409 | Duplicate email, customer code, bill month; delete of something in use |
| Unauthorized | 401 | Missing, invalid or expired token; bad login |
| Forbidden | 403 | Valid user, wrong role |
| Validation | 422 | Bad input (framework default) |
| Unhandled | 500 | Anything else; generic body, details only in logs |

One body shape for all: an `error` object with `code` and `message`. Database integrity errors are translated to Conflict before leaving the service layer.

## 6. Authentication and authorization

- Register hashes the password and stores a `customer`.
- Login verifies the hash and issues a token holding the user id and expiry.
- Each request: verify token → load user from the database → reject inactive users → read role from the row.
- Role gates are a reusable dependency. Ownership checks ("is this the customer's own connection?") live in services.
- For a resource the caller does not own, return 404 so its existence is not revealed.

## 7. Assistant

Full behaviour: `AGENT.md`. Technical points:

- The chat endpoint is stateless; the client sends the whole message list.
- Cap message count and message length per request.
- Per request: embed the last user message → retrieve chunks under the distance limit → build the prompt (system prompt, context or "no documents matched", messages) → tool loop with a round cap → return reply, tools used, sources.
- Tools receive the current user from the request, never from model arguments.
- Timeouts on LLM and embedding calls; on failure return a clear 502/503-style error body, not a stack trace.

## 8. RAG

| Item | Requirement |
|---|---|
| Storage | `knowledge_chunks` with a pgvector column and a vector index |
| Ingest | Script reads `knowledge/`, splits with overlap, embeds, upserts by (source, chunk index); safe to re-run |
| Retrieval | Top-k by cosine distance, filtered by a maximum distance |
| Settings | Top-k, maximum distance, embedding model, vector size |
| Consistency | The same embedding model for ingest and for questions |

## 9. MCP

One server object, two transports. Tools, resource and prompt are listed in `AGENT.md` section 8. The HTTP transport is mounted inside the FastAPI app at `/mcp`; the stdio transport is a separate entry point. Both obtain database sessions the same way the API does and call the same services.

## 10. Configuration

Settings and which are required: `BUILD_PLAN.md` section 9. Required secrets have no defaults. `.env.example` lists every setting with a placeholder.

## 11. Containers and deployment

| Service | Role |
|---|---|
| db | Postgres with pgvector, named volume, healthcheck |
| embeddings | Embedding server, model cached in a volume |
| backend | Built from the Dockerfile; waits for db; runs migrations then the server |

Live deployment: Render web service from the Dockerfile, Render Postgres, frontend as a static site. The embedding service needs its own host or a hosted API with the same vector size. CORS allows only the frontend origin.

## 12. Non-functional

| Area | Requirement |
|---|---|
| Security | Hashed passwords; no secrets in the repo; role from the database; tool scoping; CORS allow-list; limits on login and chat requests |
| Reliability | Health endpoint checks the database; migrations are the only schema path |
| Observability | Structured logs with request id, user id and tool names; never log tokens, passwords or full prompts with personal data |
| Performance | Indexes on foreign keys and filter columns; pagination on lists |
| Data | Money as exact decimals; timestamps with time zone; Asia/Dhaka shown in the UI |

## 13. Testing

| Kind | Covers |
|---|---|
| Unit | Services: billing rules, ownership checks |
| API | Each status code in section 5 at least once; role gates |
| Assistant | The eight acceptance scenarios in `PRD.md`, especially cross-customer access |
| Manual | Fresh clone with Docker; both MCP transports in the Inspector; live `/docs` |
