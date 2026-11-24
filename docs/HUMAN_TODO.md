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

Decision: **B** (2026-11-24). The int8 service is `embedder/`; it fits in 512 MB (about 250 MB steady, 393 MB peak), and retrieval on its vectors was checked on the eval set.

## 5a. Deploy (Phase 9)

Never paste a secret (database URL, API key, password) into the chat. Type it only into
the Neon or Render dashboard, or into your own terminal as shown below.

1. **Neon:** create a free project, region **AWS Asia Pacific (Singapore)**, database `netdesk`.
   Copy the connection string (the default one is fine; the app translates `sslmode`).
2. **Your terminal, in the repo:** put the schema, demo data and help articles into Neon.
   The int8 embedder must be running locally first (`podman run -d --name embedder-local -p 8082:8000 netdesk-embedder:spike`,
   or build it: `podman build -t netdesk-embedder:spike embedder`).
   ```bash
   read -rs NEON_URL && export DATABASE_URL="$NEON_URL"   # paste, Enter; nothing is shown
   uv run alembic upgrade head
   read -rs DEMO_PW && SEED_DEMO_PASSWORD="$DEMO_PW" uv run python -m scripts.seed   # a NEW demo password
   EMBEDDINGS_URL=http://127.0.0.1:8082 EMBEDDINGS_MODEL_LABEL=intfloat/multilingual-e5-small-qint8 \
     uv run python -m scripts.ingest --dir knowledge
   unset NEON_URL DATABASE_URL DEMO_PW
   ```
3. **Render** (the Blueprint is already created and applied; the services are live at):
   - API: https://netdesk-api-mvkc.onrender.com (dashboard: https://dashboard.render.com/web/srv-dc2hri6k1f9s7382br00)
   - Embedder: https://netdesk-embedder-mvkc.onrender.com
   - Web: https://netdesk-web-mvkc.onrender.com

   The API cannot start until you add two secrets on **its Environment page**
   (https://dashboard.render.com/web/srv-dc2hri6k1f9s7382br00/env → Add Environment Variable):
   - `DATABASE_URL` ← Neon: your project → **Connect** → turn **Connection pooling OFF** (use the
     direct string) → copy the string that starts with `postgresql://`.
   - `LLM_API_KEY` ← your Gemini key (https://aistudio.google.com/apikey).

   Save changes; Render redeploys the API by itself. Never paste these anywhere else.
4. **Delete the old failed service** `NetDesk` (Oregon; https://dashboard.render.com/web/srv-dc2ap6g8v5cc73cc8lt0
   → Settings → Delete Web Service). It was created by hand before the Blueprint and cannot start.
5. When https://netdesk-api-mvkc.onrender.com/api/v1/health answers `{"status":"ok",...}`, run the
   live smoke test (first request after idle can take about a minute):
   `read -rs PW && SMOKE_EMAIL=admin@netdesk.demo SMOKE_PASSWORD="$PW" SMOKE_CHAT=1 scripts/smoke.sh https://netdesk-api-mvkc.onrender.com`

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
