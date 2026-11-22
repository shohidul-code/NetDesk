# Phase 0 — Scope freeze: viva notes

## What was built and why

- Moved every planning doc into `docs/`, the layout PROPOSAL §6.2 and §15.2 expect; `docs/PROPOSAL.md` is the source of truth.
- Started git with a `.gitignore` that keeps `.env` out, so secrets never reach the history (rubric B1, D Git).
- Corrected the proposal's status: no code existed, so Phase 1 starts from an empty repo.
- Rewrote `BUILD_PLAN.md` as the §16 checklist: Phases 0–10, four gates, effort, cut order, and every audit fix scheduled in the phase where it becomes due.
- Brought PRD, TRD, SCHEMA, APP_FLOW and AGENT in line with the Refined plan: claim-style registration, stored chat, 12 tables, role tool sets, embedding options A/B.
- Cut the P0 frontend to 9 pages in UI, FRONTEND_AGENT_BRIEF and RULES; packages, users, knowledge and the dashboard became P1 (Swagger covers them).
- Settled six open design points in the proposal: id types, bill due date, complaint status changes, who creates complaints, soft chat delete, and 413.
- Listed the tasks only I can do in `docs/HUMAN_TODO.md`.

## Five locations to explain

- `docs/PROPOSAL.md:524`: lookup tables use `int` ids, everything else `uuid`. Lookups are small and fixed; uuids stop people guessing other customers' ids.
- `docs/PROPOSAL.md:528`: complaint status can only move forward, plus one reopen; anything else is a 409 state conflict, not a validation error.
- `docs/PROPOSAL.md:664`: 413 for bodies over 64 KB; the limit protects a 512 MB free instance from oversized requests.
- `docs/BUILD_PLAN.md:54`: `tests/test_rubric_rules.py` turns the quiet rubric slips (`create_all`, a 422 echoing input, a 500 traceback, a route without auth, `uv.lock`) into a failing test.
- `.gitignore:2`: `.env` and `.env.*` are ignored, and only `.env.example` is committed, so a secret cannot be committed by accident.

## Likely viva questions

1. **Why freeze scope before coding?** The biggest risk to the marks is too many half-finished features. A frozen P0 list and a cut order say what to drop first if time runs short.
2. **Why only 9 frontend pages?** Each page costs time, and Swagger already covers the admin screens for packages, users and knowledge. Nine polished pages beat fourteen rough ones.
3. **Why is deleting a chat a soft delete?** Chat messages are the audit trail for the AI: which tools ran and what was cited. Hiding the session keeps the record.
4. **Why may technicians not create complaints?** The access model (§7.3) gives them read and status updates only. The rubric says domain writes are admin-only, and complaints are an exception only for customers, controlled by `ALLOW_CUSTOMER_COMPLAINTS`.
5. **Why schedule fixes by phase instead of doing them now?** A fix needs the code it protects. The LRU cache needs the embedder (Phase 5), and the MCP host check needs the MCP server (Phase 6). Doing them early would mean building later phases first.

## Rubric rows this phase moves (PROPOSAL §4)

- **A Idea & originality, E1–E5:** PRD positioning, roles, metrics and pricing hypotheses are written; interviews are still to do (`HUMAN_TODO.md` §4). Status stays *Not started* until interview notes exist.
- **D Git:** repo started with `.gitignore`; small conventional commits begin with the Phase 0 docs.
- No B row completes in Phase 0; B1 starts in Phase 1.
