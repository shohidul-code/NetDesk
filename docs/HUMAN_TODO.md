# Human to-do

Tasks only you can do. Claude Code does not attempt these. Tick each box and note the date and the answer, because several answers change the build (see the "Changes" column).

## 1. Git and GitHub (before Phase 1 commits)

- [ ] Set your git identity in this repo: `git config user.name "…"` and `git config user.email "…"`.
- [ ] Create a public GitHub repo and push `main`. Gate 0 needs CI green on GitHub.

## 2. Ask the instructor, in writing (Phase 0)

Send these together (PROPOSAL §4 conflicts and "Open questions"). Keep the reply in this file.

| # | Question | Changes |
| --- | --- | --- |
| 1 | "Domain writes admin only": may customers create complaints and technicians update them? Connections, packages, bills, notices and users stay admin-only. | `ALLOW_CUSTOMER_COMPLAINTS` (true if yes) |
| 2 | Compose runs the embedding service, but Render cannot run Compose. Is a hosted copy of the same model (Hugging Face Inference, or a self-hosted embedder) acceptable in production, with RAG also shown locally in the video? | Embedding option A or B |
| 3 | Duplicate registration returns 409, which reveals that an email exists. Is that acceptable if registration is rate-limited? | Nothing if yes |
| 4 | Are pagination, document access control, MCP client tests, CI and a versioned prompt graded, or only quality targets? | Cut order if time is short |
| 5 | What is the deadline, and how long does grading take? | Cut order; cold-start plan |

- [ ] Sent on: ____ · Answer received on: ____

## 3. Ask classmates (Phase 0)

- [ ] Which LLM and which embedding model did the class use? If you reuse class code, the vector size must match (NetDesk uses `multilingual-e5-small`, 384 dims).

## 4. ISP owner interviews (before recording the video)

Do 3–5 interviews; at least 3 before the video (PROPOSAL §3 "Customer-discovery experiments").

- [ ] Use the 10 questions in `docs/PROJECT_IDEA.md`. Record their current tool, monthly support load and reaction to the price options.
- [ ] Ask one operator to tally call reasons for 7 days: bill, payment, outage, slow speed, other.
- [ ] Show the two price options (per connection vs flat tier); note which they choose and why.
- [ ] With permission, collect up to 30 real customer questions in Bangla/Banglish, anonymize them, and add them to the eval set.
- [ ] Ask which billing tool they use and whether it exports CSV.

Only these notes and sourced facts may go into the README and video; everything else is labelled a hypothesis.

## 4b. Write the help articles and eval cases (Phase 5, before Gate 2)

- [ ] 12–15 help articles in `knowledge/` (Bangla and English, incl. one archived and two staff-only).
- [ ] 20 eval cases in `eval/cases.yaml`.

Format and examples: [knowledge-template.md](knowledge-template.md).

## 5. Choose the live embedding path (Phase 5, not deploy day)

- [ ] **Option A:** Hugging Face PRO, $9/month, needs an international card. Live queries go to HF Inference with the same model.
- [ ] **Option B:** self-host an int8 build of the same model on a second Render free service ($0; shares the 750 free hours). Needs a half-day spike; keep it only if `docker stats` shows it under about 450 MB. Ingest through the same int8 service so stored and query vectors match.

Decision: ____ (A: `EMBEDDINGS_PROVIDER=hf_inference`; B: `EMBEDDINGS_URL` points at the int8 service. See PROPOSAL §12.3.)

## 5b. Check MCP in MCP Inspector (Phase 6)

- [x] Over HTTP with an admin token: list 2 tools, call `lookup_customer_bills` for ND-000005, read `netdesk://packages/active`, render `due_bill_reminder`. Record a short clip for the video (PROPOSAL §13.3, B9).
- [x] Over stdio (`uv run netdesk-mcp`, see README): the same list. Optionally add it to Claude Desktop.

## 6. Record the video (Phase 10)

Follow the storyboard in PROPOSAL §17: 5–10 minutes, your own voice, all five flows labelled.

- [ ] Record all five flows locally, so the video does not depend on free tiers.
- [ ] Call `/api/v1/health` on Render a minute before recording; re-run the seed first.
- [ ] Speak from bullet notes, not a script. Do two takes.
- [ ] Upload to Google Drive ("Anyone with the link: Viewer") and test the link while logged out.
- [ ] Record a 2-minute explanation at the end of every phase (viva rehearsal).
