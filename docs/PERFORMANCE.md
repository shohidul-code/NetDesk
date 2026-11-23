# Performance (Phase 8)

Measured on 2026-11-24 with `scripts/measure_latency.py`, against a local single-worker
uvicorn and PostgreSQL 16 in a container on an 8-core laptop, with a copy of the synthetic
demo data (30 connections, 180 bills). Each list endpoint got one warm-up request, then 50
timed requests. Chat got 5 turns with the real model (`gemini-3.5-flash-lite`, free tier),
12 s apart. Times are wall clock at the client.

| Endpoint | Requests | p50 | p95 | Status codes |
| --- | --- | --- | --- | --- |
| GET /health | 50 | 2 ms | 2 ms | [200] |
| GET /auth/me | 50 | 2 ms | 3 ms | [200] |
| GET /connections (page of 20) | 50 | 4 ms | 5 ms | [200] |
| GET /connections?q= (search) | 50 | 4 ms | 5 ms | [200] |
| GET /bills (page of 20) | 50 | 4 ms | 5 ms | [200] |
| GET /complaints | 50 | 4 ms | 16 ms | [200] |
| GET /notices | 50 | 3 ms | 5 ms | [200] |
| GET /bills (customer, own) | 50 | 5 ms | 6 ms | [200] |
| POST chat message (real model) | 5 | 6.1 s | 22.3 s | [201] |

## Reading the numbers

- **The API itself is fast.** Every list endpoint stays under 20 ms at p95, including the
  database round trips and the per-request user lookup. At this data size, exact vector
  search and simple indexes are enough; no cache is needed.
- **Chat misses the 8 s p95 target (PROPOSAL §9.9), and the cause is the model provider.**
  Stored per-turn latencies were 2.4, 22.2, 12.4, 1.4 and 6.0 s:
  - the slowest turn made **no tool call**, so it was a single model request;
  - a turn with a tool (two model requests) took 2.4 s;
  - the server log shows 2 provider retries during the run.

  Embedding a question (TEI) and retrieval take milliseconds. With 5 samples, p95 is
  simply the slowest turn.
- Earlier eval runs on the same day showed the same pattern: p50 2.8 to 9.0 s, depending
  on the free endpoint's load at the time.

## What would bring chat under 8 s

1. A paid model tier or a provider with steadier latency. This is the main lever; nothing
   in our code is close to the budget.
2. A shorter provider timeout with one retry instead of two, so a stalled call fails
   fast and the user can retry (trade-off: more 503s).
3. Streaming the reply (P2), so the first words arrive sooner, even if the total time is
   the same.

The live deploy (Phase 9) adds Render's network hop and cold start; re-measure there with
`--base-url https://<api>.onrender.com`.
