# Phase 4 — LLM, tools and chat: viva notes

## What was built and why

- An `LLMClient` interface with two implementations: the real OpenAI-compatible client (Gemini endpoint, 20 s timeout, 2 retries) and `FakeLLM`, which plays scripted replies so every test runs offline and for free.
- Any provider failure (timeout, 429, 5xx, bad key) becomes one 503 `llm_unavailable` envelope; the log keeps only the error class and status, never prompts or keys.
- Prompt v1 (PROPOSAL §9.3) lives in `support_v1.md`; its version is saved on every assistant message, so an eval result can be tied to the exact prompt.
- Four read-only tools in two role sets: customers get *their own* bill and area status; staff look up any customer or area. Each tool is a thin wrapper over one of two services that REST and MCP also use.
- The registry re-checks the role on every call: a tool the role may not use returns `tool_not_available` and logs a security warning, even if the model invents the call. Arguments are validated with Pydantic, with a 5 s timeout and a 4 KB result cap.
- Stored chat: sessions and messages with tools used, tokens, latency and model; owner-only access; soft delete.
- Each turn sends the last 12 messages, allows at most 3 tool rounds, then answers or falls back. Limits: 30/day customer, 100/day staff, 1,500/day overall (reset at Dhaka midnight), 6/minute per user, and a `CHAT_ENABLED` kill switch.
- The gate ran against real Gemini: customer1 asked "আমার বিল কত বাকি আছে?" and got the exact database amount (৳800.00, due 10 December 2026) in Bangla, via `get_my_bill_status`.
- The gate found two real-world issues the fake model could not: the old default model returned 404, and Gemini 3 needs its `thought_signature` echoed back on tool calls.

## Five locations to explain

- `app/modules/chat/services.py:160`: the tool loop. Each round the model either answers (stop) or asks for tools; results go back as `tool` messages. After 3 rounds the fallback reply is used, so a confused model cannot loop forever or run up cost.
- `app/modules/agent/registry.py:105`: `execute`. The model only *asks* for a tool; this function decides, using the role from the database, never from the model's text.
- `app/modules/chat/services.py:99`: `_check_limits`. Quotas are counted from stored user messages, including deleted sessions, so deleting a chat cannot reset a quota.
- `app/modules/chat/services.py:130`: `extra_content` echoed back. Gemini 3 signs each tool call; without the signature the next request fails with 400.
- `app/integrations/llm/client.py:64`: one `except openai.APIError` turns every provider failure into a 503, and nothing is saved, so a failed turn does not use the user's quota.

## Likely viva questions

1. **How do you stop the model reading another customer's bill?** The customer tools take no customer code at all; they use the user id from the token. If the model invents a staff tool call, the registry refuses it (`tool_not_available`). Tests force exactly this and check the refusal.
2. **What does a FakeLLM test prove, and what not?** It proves our code: tool results reach the second call, the round cap, the role filter, quotas, saving. It cannot prove the real model picks the right tool or writes good Bangla. That is what the real-model gate and the Phase 5 eval measure.
3. **Why store chat at all?** Follow-up questions need history, quotas need counts, and the stored tools used, prompt version and tokens form the audit trail for what the AI said and what it cost.
4. **Why a fixed +6 offset instead of a timezone database for Dhaka?** Bangladesh has no daylight saving, so +6 is exact all year, and the slim Docker image does not need tzdata.
5. **What happens when Gemini is down?** The user gets a 503 with a friendly message, the turn is not saved and does not count against the quota. During the gate, `gemini-3.1-flash-lite` was overloaded (503) for minutes; the default moved to `gemini-3.5-flash-lite`, which answered in under a second.

## Rubric rows this phase moves (PROPOSAL §4)

- **B6 LLM chat:** OpenAI-compatible client, versioned system prompt, stored multi-turn sessions, history window, token tracking. Done, plus the real-model gate.
- **B7 Tool calling:** role-scoped tools chosen by the model, executed by the server, results returned to the model, refusal of forbidden tools. Done and tested.
- **B5 Errors:** 429 (quota) and 503 (model or kill switch) now tested on real routes.
