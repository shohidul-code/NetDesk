# Phase 7 — Frontend: viva notes

## What was built and why

- A React + TypeScript (strict) single-page app in `frontend/`. It is built with Vite and
  uses React Router, TanStack Query for server data, Tailwind CSS with the UI.md tokens,
  shadcn/ui components, and react-hook-form + zod for forms.
- **API types are generated** from the API's `/openapi.json` (`npm run gen:api`), so the
  frontend cannot silently drift from the backend's shapes.
- **One API client** (`src/api/client.ts`) is the only place that calls `fetch`. It:
  - adds the Bearer token;
  - turns the error envelope into one typed `ApiError` (status, code, message, details,
    request_id, Retry-After);
  - ends the session on a 401 for a signed-in call.
- **Auth:** the token is kept in memory and in localStorage. On start, `/auth/me` checks
  it. Guards route each role to its home and show "No access" for other roles' pages. The
  backend still enforces every rule; the UI only routes.
- **The 9 P0 pages:** Login, Claim, Customer home, Assistant, My complaints, Technician
  queue, Connections, Bills, Notices, plus Profile. Every list has loading, empty and
  error states (the error shows the request id under "Details").
- **The assistant** keeps history on the server and sends only the new message. It shows
  tool and source chips, a distinct "No information found" bubble, and messages left
  today. It disables the composer on the daily limit (429) and keeps the typed text with a
  Retry on 503.
- **Backend fix found by planning:** `CORS_ORIGINS` was configured but never applied, so
  every browser call would have failed. `CORSMiddleware` is now the outermost layer, with
  no credentials and no wildcard, and it exposes Retry-After and X-Request-ID.
- **Supply chain:**
  - `.npmrc` sets `min-release-age=7`, like uv's 7-day cooldown.
  - The shadcn CLI was used once and then removed: it had silently added an unrelated npm
    package called `cn`, which we deleted.
  - TypeScript is pinned to 5.9 because the tooling does not support 6 or 7 yet.

## Five locations to explain

- `src/api/client.ts` and `src/api/errors.ts`: one error type, and why a non-envelope body
  (a proxy page) is never shown to the user.
- `src/auth/AuthProvider.tsx` and `src/auth/guards.tsx`: the session lifecycle and role
  routing.
- `src/features/chat/messages.ts`: the user's message is shown before the server answers,
  and the no-information rule for stored history mirrors the server's rule.
- `src/lib/format.ts`: the only money and date formatters. It uses lakh grouping
  (৳1,50,000), prints dates in UTC so a date never shifts by a day, and shows instants in
  Dhaka time.
- `app/main.py` (CORS): why the middleware is outermost.

## Likely viva questions

1. **If the UI hides admin buttons, is that the security?** No. The API refuses: 403 by
   role, 404 out of scope. The UI hiding is only usability. Acceptance check 7 opens an
   admin page as a customer and gets "No access", and the API would refuse the calls
   anyway.
2. **Why generate types instead of writing them?** The OpenAPI document is the contract.
   Regenerating after an API change turns a mismatch into a compile error instead of a
   runtime bug.
3. **Why keep the token in localStorage?** So a refresh keeps the session (the brief). The
   risk is XSS: React escapes output, the app renders no HTML strings, and the token lasts
   30 minutes. HttpOnly cookies would need CSRF protection and a different auth flow.
4. **Why TanStack Query?** Caching, retries (none on 4xx), invalidation after mutations,
   and loading and error states without hand-written effects.
5. **How was it tested?** Node's test runner covers the pure helpers (formatters, error
   parsing, Dhaka time, hours open). CI runs lint, type check, tests and build. The 11
   acceptance checks were run by hand in the browser at 360px against a copy of the demo
   database.

## Rubric rows this phase moves (PROPOSAL §4)

- **Frontend:** 9 P0 pages for three roles, error mapping, mobile-first layout, a chat UI
  with citations. Done and checked in the browser.
