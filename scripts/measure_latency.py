"""Measure p50/p95 latency of the API (Phase 8, PROPOSAL §9.9 target: chat p95 <= 8 s).

    SEED_DEMO_PASSWORD=... uv run python -m scripts.measure_latency --base-url http://localhost:8000

Lists are timed over many requests; chat over a few, because every chat turn is a real
model call on a free tier. Run it against a disposable copy of the demo database: the chat
turns are stored. Prints a Markdown table for docs/PERFORMANCE.md.
"""

import argparse
import os
import sys
import time

import httpx

from scripts.eval_chat import percentile

LIST_PATHS = [
    ("GET /health", "/api/v1/health", "admin"),
    ("GET /auth/me", "/api/v1/auth/me", "admin"),
    ("GET /connections (page of 20)", "/api/v1/connections?limit=20", "admin"),
    ("GET /connections?q= (search)", "/api/v1/connections?q=Shirin&limit=20", "admin"),
    ("GET /bills (page of 20)", "/api/v1/bills?limit=20", "admin"),
    ("GET /complaints", "/api/v1/complaints?limit=20", "admin"),
    ("GET /notices", "/api/v1/notices", "admin"),
    ("GET /bills (customer, own)", "/api/v1/bills?limit=20", "customer"),
]
CHAT_QUESTIONS = [
    "How much do I owe?",
    "রাউটার কিভাবে রিস্টার্ট করব?",
    "How do I pay by bKash?",
    "Starlink এর দাম কত?",
    "আমার এলাকায় কি কোনো সমস্যা চলছে?",
]
EMAILS = {"admin": "admin@netdesk.demo", "customer": "customer1@netdesk.demo"}


def login(client: httpx.Client, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    resp.raise_for_status()
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def timed(client: httpx.Client, method: str, path: str, **kw: object) -> tuple[float, int]:
    start = time.perf_counter()
    resp = client.request(method, path, **kw)  # type: ignore[arg-type]
    return time.perf_counter() - start, resp.status_code


def row(name: str, samples: list[float], statuses: set[int]) -> str:
    p50, p95 = percentile(samples, 50), percentile(samples, 95)
    assert p50 is not None and p95 is not None
    ms = f"{p50 * 1000:.0f} ms | {p95 * 1000:.0f} ms"
    return f"| {name} | {len(samples)} | {ms} | {sorted(statuses)} |"


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure NetDesk API latency.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--n", type=int, default=50, help="requests per list endpoint")
    parser.add_argument("--chat", type=int, default=5, help="chat turns (real model calls)")
    parser.add_argument("--pause", type=float, default=12.0, help="seconds between chat turns")
    args = parser.parse_args()
    password = os.environ.get("SEED_DEMO_PASSWORD") or sys.exit("set SEED_DEMO_PASSWORD")

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=90) as client:
        auth = {role: login(client, email, password) for role, email in EMAILS.items()}
        print("| Endpoint | Requests | p50 | p95 | Status codes |")
        print("| --- | --- | --- | --- | --- |")
        for name, path, role in LIST_PATHS:
            timed(client, "GET", path, headers=auth[role])  # warm-up, not counted
            results = [timed(client, "GET", path, headers=auth[role]) for _ in range(args.n)]
            print(row(name, [t for t, _ in results], {s for _, s in results}), flush=True)

        chat_times: list[float] = []
        statuses: set[int] = set()
        chat_id = client.post("/api/v1/chat/sessions", headers=auth["customer"]).json()["id"]
        for i, question in enumerate(CHAT_QUESTIONS[: args.chat]):
            if i:
                time.sleep(args.pause)
            took, status = timed(
                client,
                "POST",
                f"/api/v1/chat/sessions/{chat_id}/messages",
                headers=auth["customer"],
                json={"content": question},
            )
            chat_times.append(took)
            statuses.add(status)
        if chat_times:
            print(row("POST chat message (real model)", chat_times, statuses))
    return 0


if __name__ == "__main__":
    sys.exit(main())
