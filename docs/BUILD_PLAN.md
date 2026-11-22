# NetDesk — ISP Support Agent: Architecture and Build Plan

A plan for you to build by hand. It contains no backend code on purpose: Part B must be your own work (course AI policy, Section 5).

Codes like **B7** point to the marking criteria.

---

## 1. Product in one paragraph

**NetDesk** is a support and billing agent for small area broadband operators in Bangladesh. Customers ask in chat: "why is my net down?", "how much do I owe?". The agent checks the real database (bills, complaints in the area) and the operator's own documents (troubleshooting guide, packages, payment rules), then answers. Owners and technicians manage connections, bills and complaints from a dashboard.

| Sellable point (E) | NetDesk answer |
|---|---|
| Target customer | Area broadband operators with roughly 200–2,000 connections |
| Real problem | The office phone rings all day for the same three questions; bills are tracked on paper or Excel |
| Realistic use | Real fields (package, area, billing month, bKash) and real roles (owner, technician, customer) |
| Business model | Monthly fee per active connection, plus one-time setup |
| Why pay | Fewer calls, fewer missed bills, known outages answered automatically |
| Ready to show | Seed data with real-looking names, areas and months |

Put this table in the README and say it in the video.

---

## 2. Architecture

```
 Browser (React frontend)            MCP client (Inspector / desktop app)
        |  HTTPS + JWT                     |  HTTP /mcp        |  stdio
        v                                  v                   v
 +---------------------------------------------------+   +-----------+
 | FastAPI app                                       |   | stdio     |
 |  /api/v1/...  controllers                         |   | entry     |
 |       |  Depends(db, current_user, role)          |   | point     |
 |       v                                           |   +-----+-----+
 |  services  <------------- MCP server (mounted) <--------------+
 |       |          \
 |       v           \--> integrations/llm         --> LLM API
 |  repositories      \-> integrations/embeddings  --> embedding service
 +-------|-------------------------------------------+
         v
 PostgreSQL + pgvector
```

Rules that keep the structure marks (B2):

- Controllers only do HTTP: read the request, call one service, return a schema.
- Services hold the logic and never import FastAPI request objects.
- Repositories hold every query. Nothing else touches the session.
- The chat tools and the MCP tools call the **same services**. No duplicate logic.
- Everything is wired with `Depends`.

---

## 3. Folder structure

```
netdesk/
├── app/
│   ├── main.py                  app factory, routers, handlers, MCP mount
│   ├── core/
│   │   ├── config.py            pydantic-settings
│   │   ├── database.py          async engine, session, get_db
│   │   ├── security.py          hashing, JWT create/verify
│   │   ├── exceptions.py        custom error classes
│   │   └── handlers.py          global exception handlers
│   ├── modules/
│   │   ├── auth/
│   │   ├── users/
│   │   ├── packages/
│   │   ├── connections/
│   │   ├── bills/
│   │   ├── complaints/
│   │   ├── knowledge/
│   │   └── chat/
│   │        each has: controllers.py services.py repositories.py
│   │                  schemas.py models.py dependencies.py
│   ├── integrations/
│   │   ├── llm/                 client, tool-call loop helpers
│   │   └── embeddings/          client for the embedding service
│   └── mcp/
│       ├── server.py            tools, resource, prompt
│       └── stdio.py             stdio entry point
├── alembic/                     migrations
├── scripts/
│   ├── seed.py
│   └── ingest.py
├── knowledge/                   the .md documents you write
├── frontend/                    AI-assisted is allowed here only
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
└── README.md
```

A module may leave a file nearly empty (chat has no model), but keep the same six files so the layout is consistent.

---

## 4. Data model (B3)

Six tables. All have `id` and `created_at`.

| Table | Columns | Constraints |
|---|---|---|
| **users** | full_name, email, phone, password_hash, role, is_active | email unique; role is one of admin, technician, customer |
| **packages** | name, speed_mbps, monthly_price, is_active | name unique |
| **connections** | customer_code, customer_id, package_id, area, address, status, connected_on | customer_code unique (like `MIR-0042`); FKs to users and packages; status is active, suspended or disconnected |
| **bills** | connection_id, billing_month, amount, status, paid_at, method | unique (connection_id, billing_month); status unpaid or paid; method bkash, nagad or cash |
| **complaints** | connection_id, category, description, status, technician_id, resolved_at | category no_internet, slow_speed, router, billing or other; status open, assigned or resolved |
| **knowledge_chunks** | source, chunk_index, content, embedding | embedding is a pgvector column; unique (source, chunk_index) so ingest can be re-run |

Notes:

- The embedding column size must equal your embedding model's output size. Keep the number in one setting.
- The first migration runs `CREATE EXTENSION IF NOT EXISTS vector`.
- Never call `create_all`. Every table arrives through an Alembic migration.

---

## 5. API contract (B4, B5, B10)

All paths start with `/api/v1`.

| Method and path | Who | Success | Errors |
|---|---|---|---|
| POST `/auth/register` | anyone | 201 | 409 email exists, 422 |
| POST `/auth/login` | anyone | 200 + JWT | 401 (same message for wrong email and wrong password) |
| GET `/auth/me` | logged in | 200 | 401 |
| GET `/packages` | logged in | 200 | 401 |
| GET `/packages/{id}` | logged in | 200 | 404 |
| POST `/packages` | admin | 201 | 403, 409, 422 |
| PATCH `/packages/{id}` | admin | 200 | 403, 404, 409 |
| DELETE `/packages/{id}` | admin | 204 | 403, 404, 409 if in use |
| GET `/connections` | admin, technician | 200 | 403 |
| GET `/connections/me` | customer | 200 | 404 if none yet |
| GET `/connections/{id}` | admin, technician | 200 | 404 |
| POST `/connections` | admin | 201 | 403, 404 bad customer/package, 409 duplicate code |
| PATCH `/connections/{id}` | admin | 200 | 403, 404 |
| DELETE `/connections/{id}` | admin | 204 | 403, 404 |
| GET `/bills` | admin all; customer own only | 200 | 401 |
| POST `/bills` | admin | 201 | 409 same month twice |
| PATCH `/bills/{id}/pay` | admin | 200 | 404, 409 already paid |
| GET `/complaints` | admin, technician all; customer own | 200 | 401 |
| POST `/complaints` | customer (own connection), admin | 201 | 403, 404 |
| PATCH `/complaints/{id}` | admin, technician | 200 | 403, 404 |
| POST `/chat` | logged in | 200 | 401, 422 |
| GET `/health` | anyone | 200 | |

**Marked domain API (B4): `connections`.** Full CRUD, admin-only writes, and the list takes `area`, `status` and `search` (name, phone or customer code).

**Check with your instructor:** the rubric says "domain writes are admin only", but customers create complaints and technicians update them. If that is not accepted, let only admin and technician create complaints.

Error rules (B5):

- Custom classes: NotFound, Conflict, Unauthorized, Forbidden. One global handler each.
- Database unique violations are caught and turned into Conflict. The raw database message never reaches the client.
- One catch-all handler returns a plain 500 body with no stack trace.
- One error body shape everywhere, for example `{"error": {"code": "...", "message": "..."}}`.

---

## 6. Auth design (B10)

- Hash with argon2.
- JWT holds the user id and an expiry. Nothing else.
- On every request: verify the token, load the user from the database, read the **role from the database**, not from the token.
- Register always creates a `customer`. The first admin and the technicians come from the seed script; the admin can change a user's role later.
- Wrong email and wrong password return the identical 401 body.
- Two dependencies: "current user" and "require role(...)".

---

## 7. Agent design (B6, B7, B8)

**System prompt must state:** it is the support assistant of this ISP; it answers only about connections, bills, complaints and the operator's documents; it uses tools for account facts and never guesses amounts; it answers from the retrieved documents and says clearly when they do not cover the question; it replies in the user's language.

**Chat request:** the full message list (old turns plus the new one). The server keeps no chat history, which satisfies multi-turn simply.

**Chat response:** the reply, the list of tools that ran, and the document sources used. The frontend shows these, and they make the demo easy to follow.

**Tools (both read the real database through services):**

| Tool | Input from the model | Returns |
|---|---|---|
| Bill status | none for a customer; a customer code for staff | unpaid months, total due, last payment date |
| Open complaints by area | area name (defaults to the customer's own area) | count, oldest open complaint, categories |

**Security rule:** the tool takes the user from the JWT, never from the model's arguments. A customer must not be able to read another customer's bill by asking. Staff may pass a customer code.

**Tool loop:** send messages and tool definitions → if the model asks for a tool, run it, append the result, call again → stop when the model answers in text. Cap the loop at a few rounds.

**RAG flow per question:**

1. Embed the latest user message.
2. Fetch the nearest chunks by vector distance.
3. Drop chunks beyond a distance limit (a setting you tune).
4. If chunks remain, add them to the prompt as context with their sources.
5. If none remain, tell the model no document matched, and the system prompt makes it say so.

Test question for "nothing found": something the documents do not cover, like "Do you sell Starlink?".

**Ingest script:** read each file in `knowledge/`, split into overlapping chunks, embed, upsert by (source, chunk_index).

**Documents to write (in `knowledge/`):** troubleshooting, packages and prices, payment guide, policies (house shift, reconnect fee, support hours), FAQ.

---

## 8. MCP design (B9)

| Piece | What |
|---|---|
| Tool 1 | Bill status by customer code |
| Tool 2 | Open complaints by area |
| Resource | Active package list |
| Prompt | Due-bill reminder message for a customer |
| HTTP | Mounted in the FastAPI app at `/mcp` |
| stdio | A separate entry point that starts the same server |

- Both transports import one server object, and that server calls the same services as the chat tools.
- MCP has no logged-in customer, so its tools take a customer code. Treat it as a staff-side interface and say so in the README.
- Test both transports with the MCP Inspector before recording.
- Follow the class code and the SDK docs for the exact mounting steps; the SDK changes between versions.

---

## 9. Settings (B1)

Every one of these appears in `.env.example` with a fake value.

| Setting | Required secret? |
|---|---|
| DATABASE_URL | yes |
| JWT_SECRET | yes |
| JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES | no, has default |
| LLM_API_KEY | yes |
| LLM_MODEL | no |
| EMBEDDING_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIM | no |
| RAG_TOP_K, RAG_MAX_DISTANCE | no |
| CORS_ORIGINS | no |
| SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD | yes for the seed script |

Required secrets have **no default**, so the app crashes at start when one is missing. Prove it once and show it in the video.

---

## 10. Docker (B11)

Three services in `docker-compose.yml`:

| Service | Notes |
|---|---|
| db | A Postgres image that ships with pgvector; a named volume; a healthcheck |
| embeddings | The embedding server your class used; a volume for the model so it is not downloaded every start |
| backend | Built from your Dockerfile; starts after db is healthy; runs migrations, then the server |

Final test: clone into a new folder, copy `.env.example` to `.env`, fill in the keys, run `docker compose up`, then the seed and ingest commands exactly as the README says. If any step needs knowledge that is not in the README, fix the README.

---

## 11. Step by step

Commit after each step with the message shown.

**Phase 0 — Repo**
1. Create the repo. Add `.gitignore` first (`.env`, `.venv`, `__pycache__`). → `chore: init repo`

**Phase 1 — Setup (B1)**
2. Start the project with uv; add dependencies; commit `pyproject.toml` and `uv.lock`. → `chore: add dependencies`
3. Write settings and `.env.example`. Start the app with a secret removed and see it fail. → `feat: settings with required secrets`
4. Create the app, the `/api/v1` router and the health endpoint. → `feat: app skeleton and health`

**Phase 2 — Docker early (B11)**
5. Write the Dockerfile and compose file with db and embeddings. Bring the stack up. → `feat: docker compose stack`

**Phase 3 — Database (B3)**
6. Async engine, session and `get_db`. → `feat: async database session`
7. Set up Alembic for async. First migration: vector extension and users. → `feat: users table migration`

**Phase 4 — Errors and auth (B5, B10)**
8. Custom exceptions and global handlers. → `feat: global error handlers`
9. Hashing and JWT helpers. → `feat: password hashing and jwt`
10. Register, login, me, and the two dependencies. Test 401, 403 and the identical login error. → `feat: auth endpoints and roles`

**Phase 5 — Domain (B2, B4)**
11. Packages: model, migration, repository, service, controller. → `feat: packages crud`
12. Connections with filters and search. → `feat: connections crud with filters`
13. Bills. → `feat: bills`
14. Complaints. → `feat: complaints`
15. Seed script: admin, technicians, customers, packages, connections, three months of bills, complaints. → `feat: seed script`
16. Walk every status code in Swagger: 201, 404, 409, 401, 403, 422. → `fix: ...` as needed

**Phase 6 — LLM chat (B6)**
17. LLM client inside `app/integrations/llm/`. → `feat: llm integration layer`
18. Chat endpoint with system prompt and multi-turn. → `feat: chat endpoint`

**Phase 7 — Tools (B7)**
19. Bill status tool end to end. → `feat: bill status tool`
20. Complaints-by-area tool. → `feat: area complaints tool`
21. Test as customer A asking for customer B's bill; it must fail. → `fix: scope tools to current user`

**Phase 8 — RAG (B8)**
22. Knowledge table migration. → `feat: knowledge chunks table`
23. Embedding client. → `feat: embedding integration`
24. Write the documents; write the ingest script. → `feat: ingest script and documents`
25. Retrieval inside chat, with the distance limit and the "nothing found" answer. → `feat: rag in chat`

**Phase 9 — MCP (B9)**
26. Server with two tools, the resource and the prompt. → `feat: mcp server`
27. Mount at `/mcp`. → `feat: mcp over http`
28. stdio entry point. Test both in the Inspector. → `feat: mcp over stdio`

**Phase 10 — Frontend (C2, C5)**
29. Build from `FRONTEND_AGENT_BRIEF.md`. AI is allowed here. → `feat: frontend`

**Phase 11 — Ship (D, Section 2)**
30. README: what and who, setup, example requests, business model, three links. → `docs: readme`
31. Deploy (Section 12). → `chore: deploy config`
32. Fresh-clone test. → `fix: ...` as needed

**Phase 12 — Video (C)**
33. Record 5–10 minutes (Section 13). Upload to Drive, set "Anyone with the link can view", add the link to the README.

---

## 12. Deploy on Render

1. Create a Postgres database on Render. The first migration enables the vector extension.
2. Create a web service from your Dockerfile. Set every setting from `.env.example` in the dashboard.
3. Run migrations on start. Run seed and ingest once against the Render database.
4. **Embedding service:** compose does not run on Render. Either host the embedding container as a second service, or point `EMBEDDING_BASE_URL` at a hosted embedding API with the same vector size. Decide this early; it is the most likely blocker.
5. Deploy the frontend as a static site. Add its address to `CORS_ORIGINS`.
6. Open `<your-url>/docs` in a private window. This is what the marker opens.
7. Free services can sleep and free databases can expire. Check Render's current limits, and open the link shortly before the marking date.

---

## 13. Video outline

| Minutes | Show |
|---|---|
| 0–1 | What NetDesk is, who buys it, the problem, the frontend |
| 1–5 | The five flows, pointing at your files: API, chat + tools, RAG, MCP, auth |
| 5–7 | Live: login, a CRUD call, a chat that uses a tool, a RAG answer, a "nothing found" answer, MCP in the Inspector |
| 7–9 | Your own code: why layers, why role from the database, why the tool ignores model-supplied user ids |
| 9–10 | Business model and the three links |

---

## 13a. Real-product depth

A demo shows that features exist. A real product handles what happens in an actual ISP office. Finish every rubric item first, then add these in order; each is small.

**Talk to one real operator first.** Ask your own ISP's office: how do they bill, what do customers call about, when do they cut a line? Thirty minutes of answers will shape your fields, documents and seed data better than anything else, and gives you a true story for the video.

| # | Real-world rule | What it adds |
|---|---|---|
| 1 | Bills are created for everyone at the start of a month | An admin action "generate bills for this month" that skips connections already billed |
| 2 | Payments have a trail | Transaction ID and "received by" on a paid bill |
| 3 | Lines get cut for non-payment | Connections with two or more unpaid months can be suspended, and paying reactivates them |
| 4 | Complaints have a life cycle | Timestamps for opened, assigned, resolved; "hours open" shown to staff |
| 5 | Outages hit a whole area | An area notice the admin posts ("fibre cut in Mirpur 10, fixed by 6pm"); the complaints tool returns it, so the agent tells customers before they complain |
| 6 | Lists get long | Pagination and sorting on every list endpoint |
| 7 | Records are not really deleted | Deleting a connection that has bills is refused with 409; it is disconnected instead |
| 8 | Owners want numbers | A summary endpoint: active connections, this month's collected and due, open complaints per area |
| 9 | Customers write in Bangla | Documents in both languages; test Bangla questions against retrieval |
| 10 | Abuse happens | A limit on login attempts and on chat requests per user |

**Seed data that looks real:** Bangladeshi names, real Dhaka areas, package names like "Home 20 Mbps", three months of bills where most are paid and some are late, complaints with believable text, one area with a cluster of open complaints so the outage flow can be shown.

**Small things markers and buyers both notice:** consistent error bodies, clear Swagger descriptions and examples on every endpoint, a health endpoint that checks the database, structured logs without secrets, and a few tests on auth and the tool scoping rule.

---

## 14. Requirement checklist

Tick every line before you submit.

**B1 Setup**
- [ ] uv, with `pyproject.toml` and `uv.lock` committed
- [ ] Every endpoint under `/api/v1`
- [ ] Settings via pydantic-settings from `.env`
- [ ] `.env.example` lists every setting; real `.env` not committed
- [ ] App refuses to start when a required secret is missing

**B2 Structure**
- [ ] One folder per feature under `app/modules/`
- [ ] Each has controllers, services, repositories, schemas, models, dependencies
- [ ] Controllers do HTTP only; logic in services; queries in repositories; `Depends` everywhere

**B3 Database**
- [ ] PostgreSQL with async SQLAlchemy
- [ ] 3+ tables including users and a domain table
- [ ] Every change through Alembic; no `create_all`
- [ ] Seed script fills the domain table

**B4 Domain API**
- [ ] Create, list, get one, update, delete
- [ ] Pydantic request and response schemas
- [ ] List has a filter or search

**B5 Errors**
- [ ] Custom not found, conflict, unauthorized, forbidden with global handlers
- [ ] 201, 404, 409, 401, 403, 422 all correct
- [ ] No stack traces or raw database errors in responses

**B6 LLM chat**
- [ ] Calls go through `app/integrations/llm/`
- [ ] System prompt sets role and limits
- [ ] Endpoint accepts previous messages
- [ ] Works on the live link

**B7 Tools**
- [ ] 2+ tools on the real database
- [ ] The model decides when to call
- [ ] Your code runs the tool, returns the result, and the answer uses it

**B8 RAG**
- [ ] Knowledge table with a pgvector column
- [ ] Ingest script chunks, embeds, stores
- [ ] Answers come from retrieved chunks
- [ ] Says so when nothing relevant is found

**B9 MCP**
- [ ] 2+ tools, 1 resource, 1 prompt
- [ ] Works over HTTP at `/mcp`
- [ ] Works over stdio
- [ ] Uses the real services and database

**B10 Auth**
- [ ] POST `/auth/register`, POST `/auth/login` (JWT), GET `/auth/me`
- [ ] argon2 or bcrypt
- [ ] Tokens expire
- [ ] 2+ roles read from the database
- [ ] Domain writes admin only
- [ ] Same login error for wrong email and wrong password

**B11 Docker**
- [ ] Dockerfile
- [ ] Compose starts backend, Postgres with pgvector, embedding service
- [ ] Fresh clone + README steps = working app

**C Video and UI**
- [ ] 5–10 minutes, own voice, editor and running app visible
- [ ] Overview, all five flows, live demo, own-code walk-through
- [ ] User-friendly frontend shown

**D README and Git**
- [ ] What it does and who it is for
- [ ] Setup: clone, `.env`, Docker, migrations, seed, ingest
- [ ] Example requests for login, CRUD and chat
- [ ] Three links: repo, Drive video, live Swagger
- [ ] Small commits with `feat:`, `fix:`, `docs:`
- [ ] No `.env`, secrets, `__pycache__` or `.venv` in history

**E Sellable**
- [ ] Named customer, real problem, realistic fields and roles
- [ ] Business model stated in README or video
- [ ] Why someone would pay
- [ ] Demo works end to end with real-looking data

**Section 2 links**
- [ ] Repo opens for anyone
- [ ] Drive video set to "Anyone with the link can view"
- [ ] Live link opens Swagger at `/docs`
