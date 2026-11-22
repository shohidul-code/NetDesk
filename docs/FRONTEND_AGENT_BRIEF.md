# NetDesk Frontend — Brief for an AI Coding Agent

You are building **only the frontend** of NetDesk, in Phase 7. Source: `docs/PROPOSAL.md` §11 (also §5, §8.1, §8.3). The backend code comes from the student's Claude Code sessions plus the student's own edits. You never touch it. You start only after the API contract is stable (after Phase 3, PROPOSAL §16).

## Hard rules

1. Work only inside the `frontend/` folder.
2. Do **not** create, edit or suggest changes to anything outside `frontend/`: `app/`, `migrations/`, `scripts/`, `tests/`, `compose.yaml`, `Dockerfile`, `render.yaml`, `.github/`, `docs/`, `pyproject.toml`.
3. If an endpoint behaves differently from this brief, stop and report the difference. Do not work around it by changing the backend.
4. No mock data in the final build. Every screen reads from the real API.

## Product

NetDesk is a Bangla-first support and dues assistant for small broadband operators in Bangladesh. Three kinds of people use it:

| Role | Needs |
|---|---|
| customer | See own connection, bills and notices; manage own complaints; chat with the assistant |
| technician | Work the complaint queue; view connections read-only; chat |
| admin (owner) | Manage connections, bills and notices; see complaints; chat |

Users are often on a phone, on a slow connection, and may type in Bangla or English.

## Stack (PROPOSAL §11.1)

- React + TypeScript + Vite
- React Router
- TanStack Query for server state
- Tailwind CSS + shadcn/ui
- react-hook-form + zod for forms
- API types generated from `/openapi.json` with openapi-typescript
- API base URL from `VITE_API_BASE_URL`, with `frontend/.env.example` committed

Anything beyond this list needs the student's approval first.

## API

Base path: `{VITE_API_BASE_URL}/api/v1`. Send `Authorization: Bearer <token>` on every call except register and login. Login is an OAuth2 password form.

Read `/openapi.json` first and generate your types from it. It is the source of truth over this table. Paths below follow PROPOSAL §8.1.

| Method and path | Use |
|---|---|
| POST `/auth/register` | Claim account: customer code, phone, email, password. 404 no matching connection; 409 email taken or already claimed |
| POST `/auth/login` | Form login; returns the JWT. 401 is the same for any failure; 429 |
| GET `/auth/me` | Current user and role |
| GET `/areas` | Area list for filters |
| GET `/packages?active=` | Package list (read only in P0) |
| GET `/connections?area_id&status&package_id&q&limit&offset&sort` | Admin and technician list; customer sees own |
| GET `/connections/{id}` | One connection |
| POST, PATCH, DELETE `/connections[/{id}]` | Admin only. 409 code taken; 409 bills exist on delete |
| GET `/bills?connection_id&period&status&limit&offset` | Scoped list |
| POST `/bills/generate` | Admin; returns created and skipped counts |
| POST `/bills/{id}/payment` | Admin verifies a payment with a TrxID. 409 already paid or TrxID reused |
| POST `/complaints` | Customer (own connection) or staff. 403 when the flag is off |
| GET `/complaints?status&area_id&limit&offset` | Scoped list |
| PATCH `/complaints/{id}` | Technician or admin updates status. 409 invalid status change |
| GET `/notices?area_id&active=` | Scoped list; customers see their area's notices |
| POST, PATCH `/notices[/{id}]` | Admin only |
| POST `/chat/sessions` | Start a chat session |
| GET `/chat/sessions` | Own sessions |
| GET `/chat/sessions/{id}/messages` | History of one session |
| POST `/chat/sessions/{id}/messages` | Send one message; returns the reply |
| DELETE `/chat/sessions/{id}` | Delete a session |

Out of P0 (use Swagger, do not build): `/users`, package writes, `/bills/summary`, `/knowledge/documents`, `/mcp`.

### Chat

The server stores sessions and messages. Keep the session id, create a session with `POST /chat/sessions`, then send only the new message `{content}` (1 to 1000 characters) to `/chat/sessions/{id}/messages`. Do not resend the history. To show an old chat, load it with `GET /chat/sessions/{id}/messages`.

The reply holds the text, `tools_used` (name, ok), and `sources` (ref, document title). Show a tool chip per tool and a source chip per source. A no-information reply gets a distinct style and is never hidden or rephrased. Show "messages left today" in the header. 429 means the daily limit: disable the composer. 503 means the assistant is offline: show a message and Retry.

### Errors (PROPOSAL §8.3)

Every error is `{"error": {"code", "message", "details", "request_id"}}`. Map `code` to friendly text and show `request_id` under "Details". For 422, `details` is a list of `{field, message}`; the API never echoes the submitted value.

| Status | UI behaviour |
|---|---|
| 401 | Clear the token and go to Login |
| 403 | "No access" page or message |
| 404 | Not-found state in place |
| 409 | Show the server message next to the form (for example, duplicate customer code, reused TrxID) |
| 422 | Field-level messages under the inputs |
| 429 | Login: "Too many attempts". Chat: daily limit. Respect `Retry-After` |
| 503 | "The assistant is temporarily offline" |
| 500 or network failure | "Something went wrong, try again" with a retry button |

Never show raw JSON or a stack trace.

## Screens (9 P0 pages, PROPOSAL §11.2)

| Page | Role |
|---|---|
| Login | All |
| Claim account | Customer |
| Customer home: connection card, current bill and bill list, due total, active area notices, latest complaint | Customer |
| Assistant: session list, chat, tool and source chips | All |
| My complaints: list and create form | Customer |
| Technician queue: filter by area and status, update status | Technician |
| Connections: table, filters, search, pages, create/edit drawer, delete confirm | Admin (technician read-only) |
| Bills: generate a month, list, verify payment | Admin |
| Notices: post and end a notice per area | Admin |

Also a Profile page (`/auth/me`, sign out).

**P1, out of scope for now:** Packages admin, Users, Knowledge, owner Dashboard, Bangla/English toggle, Playwright smoke test.

Route guard: after login, call `/auth/me` and send each role to its own home. The menu comes from `me.role`. A user who opens a route for another role sees "No access" or is sent home. The backend still enforces every rule.

## Chat screen details

- Message bubbles, user on the right, assistant on the left.
- The user's message appears at once; a "Thinking…" row shows while the request runs. No streaming (P2).
- `aria-live` on the reply area.
- Three suggestion chips on an empty chat: "How much do I owe?", "My internet is down", "How do I pay by bKash?".
- Disable send during a request; Enter sends, Shift+Enter adds a line.
- "New chat" creates a new session.

## Design

Full detail is in `docs/UI.md`. In short:
- Mobile first; usable at 360px. Tables collapse to cards under 640px.
- Calm utility look: one accent colour, clear status colours with a word beside each.
- Money `৳1,200`; months `Oct 2026`.
- Load a Bangla web font such as Noto Sans Bengali.
- Every list has loading, empty and error states.
- Forms validate before sending and keep the user's input when the server rejects it.
- Keyboard reachable, visible focus, labelled inputs, contrast at least 4.5:1.

## Auth handling

- Keep the token in memory and in `localStorage` so a refresh keeps the session.
- On app start, if a token exists, call `/auth/me`; on 401, clear it. The token lasts 30 minutes and there is no refresh token.
- Logout clears the token and cached data.

## Deliverables

- `frontend/` with the app, `README.md` (how to run and build) and `.env.example`
- `npm run dev`, `npm run build`, lint and type check all work
- Builds to static files for a Render static site with an SPA rewrite (`/*` → `/index.html`)
- No secrets in the code; the only setting is the API base URL

## Acceptance check

1. Claim an account with a seeded customer code and phone, log in, and land on the customer home.
2. A wrong code and phone shows the 404 message; a claimed connection shows the 409 message.
3. Log in as admin; create, edit, filter, search and delete a connection.
4. Create a connection with a duplicate customer code and see the 409 message beside the form.
5. Generate bills for a month and see created and skipped counts; verify a payment, then reuse the TrxID and see the 409.
6. Post an outage notice for an area; a customer in that area sees it on home.
7. Log in as customer and open an admin route; get "No access" or a redirect.
8. Ask the assistant "How much do I owe?" and see a tool chip; reload and reopen the session to see the history.
9. Ask a troubleshooting question and see source chips; ask something off-topic and see the distinct no-information style.
10. Let the token expire (or delete it); the next call returns to Login.
11. Everything above works at 360px width.
