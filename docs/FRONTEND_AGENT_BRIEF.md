# NetDesk Frontend — Brief for an AI Coding Agent

You are building **only the frontend** of NetDesk. The backend already exists and is written by the student by hand.

## Hard rules

1. Work only inside the `frontend/` folder.
2. Do **not** create, edit or suggest changes to any backend file (`app/`, `alembic/`, `scripts/`, `Dockerfile`, `docker-compose.yml`, `pyproject.toml`). The course forbids AI-written backend code.
3. If an endpoint behaves differently from this brief, stop and report the difference. Do not work around it by changing the backend.
4. No mock data in the final build. Every screen reads from the real API.

## Product

NetDesk is a support and billing assistant for small broadband operators in Bangladesh. Three kinds of people use it:

| Role | Needs |
|---|---|
| customer | See own connection, bills and complaints; chat with the assistant |
| technician | See and update complaints, filtered by area |
| admin (owner) | Manage packages, connections, bills, complaints |

Users are often on a phone, on a slow connection, and may type in Bangla or English.

## Stack

- React, Vite, TypeScript
- Tailwind CSS
- React Router
- Plain `fetch` wrapped in one small API client (no heavy data library needed)
- API base URL from `VITE_API_BASE_URL`, with `frontend/.env.example` committed

## API

Base path: `{VITE_API_BASE_URL}/api/v1`. Send `Authorization: Bearer <token>` on every call except register and login.

The exact request and response fields are in the backend's Swagger page at `/docs`. **Read `/openapi.json` first** and generate your types from it; treat it as the source of truth over this table.

| Method and path | Use |
|---|---|
| POST `/auth/register` | Sign up (always becomes a customer) |
| POST `/auth/login` | Returns the JWT |
| GET `/auth/me` | Current user and role |
| GET `/packages`, GET `/packages/{id}` | List and view packages |
| POST, PATCH, DELETE `/packages...` | Admin only |
| GET `/connections?area=&status=&search=` | Admin and technician list |
| GET `/connections/me` | Customer's own connection |
| GET `/connections/{id}` | One connection |
| POST, PATCH, DELETE `/connections...` | Admin only |
| GET `/bills?connection_id=&status=` | Admin sees all; customer sees own |
| POST `/bills` | Admin creates a bill |
| PATCH `/bills/{id}/pay` | Admin marks paid |
| GET `/complaints?area=&status=` | Staff see all; customer sees own |
| POST `/complaints` | Customer or admin creates |
| PATCH `/complaints/{id}` | Staff update status or technician |
| POST `/chat` | Chat with the assistant |

### Chat

Request: the whole conversation so far, oldest first, as a list of `{role, content}` messages. The server stores no history, so keep the list in component state and resend it each time.

Response: the assistant's reply, a list of tools that ran, and a list of document sources used.

### Errors

Errors share one shape with a code and a message. Handle them like this:

| Status | UI behaviour |
|---|---|
| 401 | Clear the token and go to the login page |
| 403 | Show "You don't have permission for this" |
| 404 | Show a not-found state in place |
| 409 | Show the server's message next to the form (for example, duplicate customer code) |
| 422 | Show field-level messages under the inputs |
| 5xx or network failure | Show "Something went wrong, try again" with a retry button |

Never show raw JSON or a stack trace to the user.

## Screens

**Public**
- Login
- Register

**Customer**
- Home: connection card (package, speed, area, status), total due, latest open complaint
- Bills: list by month with paid/unpaid badges
- Complaints: own list; "New complaint" form with category and description
- Assistant: the chat screen

**Technician**
- Complaints board: filter by area and status; open one to assign it to self or mark it resolved

**Admin**
- Connections: table with area and status filters and a search box; create, edit and delete with a confirm step
- Packages: list, create, edit, deactivate, delete
- Bills: filter by status; create a bill; mark paid with payment method
- Complaints: same board as technician, plus assigning to any technician
- Assistant: the chat screen (admin can ask about any customer code)

Route guard: after login, call `/auth/me` and send each role to its own home. A user who opens a route for another role is redirected to their own home.

## Chat screen details

- Message bubbles, user on the right, assistant on the left.
- Under an assistant message, show small badges for each tool that ran (for example "Checked your bill") and a collapsible "Sources" list of documents used.
- When the reply says nothing relevant was found, show it as a normal message; do not hide or rephrase it.
- Three suggestion chips on an empty chat: "How much do I owe?", "My internet is down", "How do I pay by bKash?".
- Typing indicator while waiting; disable the send button during a request; Enter sends, Shift+Enter adds a line.
- A "New chat" button that clears the list.

## Design

- Mobile first; usable at 360px wide. Tables become stacked cards on small screens.
- Calm, trustworthy look suited to a utility: one accent colour, generous spacing, clear status colours (green paid/active, amber open/unpaid, red suspended).
- Money shown as `৳1,200`. Months shown as `Oct 2026`.
- Text must render Bangla correctly; pick a font stack that includes a Bangla face.
- Every list has loading, empty and error states.
- Forms validate before sending and keep the user's input when the server rejects it.
- Keyboard reachable, visible focus, labelled inputs, sufficient contrast.

## Auth handling

- Keep the token in memory and in `localStorage` so a refresh keeps the session.
- On app start, if a token exists, call `/auth/me`; on 401, clear it.
- Logout clears the token and the chat list.

## Deliverables

- `frontend/` with the app, `README.md` (how to run and build) and `.env.example`
- `npm run dev` and `npm run build` both work
- Builds to static files that can be hosted as a static site
- No secrets in the code; the only setting is the API base URL

## Acceptance check

1. Register a new customer, log in, and land on the customer home.
2. Log in as admin; create, edit, filter, search and delete a connection.
3. Create a connection with a duplicate customer code and see the 409 message beside the form.
4. Log in as customer and open an admin route; get redirected.
5. Ask the assistant "How much do I owe?" and see a tool badge.
6. Ask a troubleshooting question and see sources.
7. Ask something off-topic and see the "nothing found" reply shown plainly.
8. Let the token expire (or delete it); the next call returns to login.
9. Everything above works at 360px width.
