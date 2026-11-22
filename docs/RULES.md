# Rules — for an AI coding agent working in this repository

Read this file before doing anything.

## 1. Scope: frontend only

This is a graded university project. This agent builds `frontend/` only, in Phase 7. Backend code comes from the owner's Claude Code sessions (see `CLAUDE.md`) plus the owner's own edits; this agent never touches it. `frontend/` is not touched before Phase 7.

| You may | You must not |
|---|---|
| Create and edit files inside `frontend/` | Create, edit, format, refactor or delete anything outside `frontend/` |
| Read backend files and `/openapi.json` to understand the API | Write or suggest backend code, migrations, scripts, Dockerfiles, compose files, CI files or docs |
| Report a backend bug or a mismatch with the docs | Fix it yourself, or work around it by changing the API contract |

If a task cannot be completed without a backend change, stop and explain what is needed. The owner will make the change.

## 2. Read first

| File | Use |
|---|---|
| `docs/FRONTEND_AGENT_BRIEF.md` | What to build and how to accept it |
| `docs/UI.md` | Design tokens, components, pages, states |
| `docs/APP_FLOW.md` | Screen map and user flows |
| `docs/PRD.md` | Requirements and acceptance scenarios |
| `docs/PROPOSAL.md` §11 | Source of truth for the frontend plan (also §5, §8.1, §8.3) |
| Backend `/openapi.json` | Source of truth for request and response shapes |

When this documentation and the running API disagree, the API wins. Report the difference.

## 3. Stack

The PROPOSAL §11.1 stack only: React, Vite, TypeScript (strict), React Router, TanStack Query, Tailwind CSS, shadcn/ui, react-hook-form and zod. API types are generated from `/openapi.json` with openapi-typescript. Anything beyond this list needs the owner's approval first.

## 4. Structure inside `frontend/`

```
frontend/
├── src/
│   ├── api/          client, generated types, typed endpoint functions, error type
│   ├── auth/         token storage, auth context, route guards
│   ├── components/   shared UI (shadcn/ui and small wrappers)
│   ├── features/     one folder per area: bills, complaints, connections, notices, chat
│   ├── layouts/      customer shell, staff shell
│   ├── pages/        route-level components (the 9 P0 pages and Profile)
│   ├── lib/          formatters for money, dates
│   └── main.tsx
├── .env.example      VITE_API_BASE_URL
└── README.md
```

## 5. Code rules

1. TypeScript strict; no `any`. Types for API data come from the generated OpenAPI types.
2. All network calls go through the API client and TanStack Query hooks. No `fetch` inside components.
3. The API client attaches the token, parses the error envelope `{"error": {"code", "message", "details", "request_id"}}` and throws one typed error.
4. Function components and hooks only. Keep components small; split when a file passes roughly 200 lines.
5. Design tokens from `docs/UI.md` live in the Tailwind config. No hard-coded hex colours in components.
6. Every list and form handles loading, empty, error and success.
7. No mock data, placeholder text or fake delays in committed code.
8. No secrets. The only configuration is `VITE_API_BASE_URL`.
9. Money, months and dates are formatted only through the helpers in `lib/`.
10. No `console.log` left in committed code.

## 6. Behaviour rules

- 401 from any call clears the session and routes to Login.
- Role decides the home route and visible navigation; a wrong-role route redirects home or shows "No access". The backend still enforces every rule.
- Build only the 9 P0 pages (see `docs/UI.md`). P1 pages (packages, users, knowledge, dashboard) wait.
- Show errors from the envelope: friendly text by `code`, and `request_id` under "Details". Handle 401, 403, 404, 409, 422, 429 and 503.
- Forms validate before sending and keep the user's input when the server rejects it.
- Buttons disable while their request is in flight, so nothing is submitted twice.
- Destructive actions ask for confirmation and name the item.
- Chat history lives on the server. Keep the session id and send only the new message; never resend the whole history.

## 7. Quality bar

- Usable at 360px wide.
- Bangla text renders correctly.
- Keyboard accessible, visible focus, labelled inputs.
- `npm run build`, type check and lint finish with no errors.

## 8. Working method

1. One page or feature per task. Do not build ahead.
2. Before coding, state which files you will add or change.
3. After coding, run the type check, lint and build, and test against the real backend.
4. Report: what was built, how it was checked, anything that differs from the docs.
5. Never say a task is done if the build fails or the page was not exercised against the API.

## 9. Git

- Small commits, one purpose each, prefixed `feat:`, `fix:`, `test:`, `docs:` or `chore:`.
- Never commit `.env`, `node_modules`, or build output.
- Do not rewrite history or force-push.
- Do not touch commits or files that belong to the backend.

## 10. When unsure

Ask. A short question is better than a wrong assumption, especially about anything near the backend boundary.
