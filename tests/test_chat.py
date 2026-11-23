"""Stored chat with the tool loop (PROPOSAL §6.7, §9.4, §9.8), run against FakeLLM."""

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.llm.client import get_llm_client
from app.integrations.llm.fake import FakeLLM
from app.integrations.llm.prompts import PROMPT_VERSION
from app.modules.chat.models import ChatMessage, ChatSession
from app.modules.chat.services import day_start
from app.modules.users.models import User
from tests.factories import make_bill, make_connection

AsUser = Callable[[str], Awaitable[User]]


def use_llm(app: FastAPI, fake: FakeLLM) -> FakeLLM:
    app.dependency_overrides[get_llm_client] = lambda: fake
    return fake


async def new_chat(client: AsyncClient) -> str:
    response = await client.post("/api/v1/chat/sessions")
    assert response.status_code == 201
    return str(response.json()["id"])


async def say(client: AsyncClient, chat_id: str, text: str) -> Any:
    return await client.post(f"/api/v1/chat/sessions/{chat_id}/messages", json={"content": text})


async def add_user_messages(db: AsyncSession, user: User, count: int, at: datetime) -> None:
    """Insert past user messages directly, to test quotas without calling the model."""
    chat = ChatSession(user_id=user.id, title="old")
    db.add(chat)
    await db.flush()
    db.add_all(
        ChatMessage(session_id=chat.id, role="user", content="hi", created_at=at)
        for _ in range(count)
    )
    await db.flush()


async def test_create_and_list_sessions(client: AsyncClient) -> None:
    chat_id = await new_chat(client)

    listed = await client.get("/api/v1/chat/sessions")

    assert [s["id"] for s in listed.json()] == [chat_id]


async def test_reply_is_saved_with_usage_and_prompt_version(
    app: FastAPI, client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    await as_user("customer")
    use_llm(app, FakeLLM([FakeLLM.text("হ্যালো! কীভাবে সাহায্য করতে পারি?")]))
    chat_id = await new_chat(client)

    response = await say(client, chat_id, "হ্যালো")

    assert response.status_code == 201
    body = response.json()
    assert body["content"] == "হ্যালো! কীভাবে সাহায্য করতে পারি?"
    assert body["tools_used"] == [] and body["sources"] == []
    assert body["usage"] == {"input_tokens": 100, "output_tokens": 20}
    assert body["messages_left_today"] == 29
    saved = (await db_session.execute(select(ChatMessage).order_by(ChatMessage.role))).scalars()
    roles = {m.role: m for m in saved}
    assert roles["user"].content == "হ্যালো"
    assert roles["assistant"].prompt_version == PROMPT_VERSION
    assert roles["assistant"].input_tokens == 100


async def test_first_message_becomes_the_title(app: FastAPI, client: AsyncClient) -> None:
    use_llm(app, FakeLLM([FakeLLM.text("ok")]))
    chat_id = await new_chat(client)

    await say(client, chat_id, "x" * 80)
    sessions = (await client.get("/api/v1/chat/sessions")).json()

    assert sessions[0]["title"] == "x" * 60


async def test_tool_result_reaches_the_second_model_call(
    app: FastAPI, client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    connection = await make_connection(db_session, customer_user_id=customer.id)
    await make_bill(db_session, connection.id, period="2026-11")
    fake = use_llm(
        app,
        FakeLLM([FakeLLM.tool("get_my_bill_status", {}), FakeLLM.text("আপনার বিল ৳1000.00")]),
    )
    chat_id = await new_chat(client)

    response = await say(client, chat_id, "আমার বিল কত?")

    assert response.json()["tools_used"] == [{"name": "get_my_bill_status", "ok": True}]
    second_call_messages = fake.calls[1][0]
    tool_messages = [m for m in second_call_messages if m["role"] == "tool"]
    assert "1000.00" in tool_messages[0]["content"]


async def test_customer_is_offered_only_customer_tools(
    app: FastAPI, client: AsyncClient, as_user: AsUser
) -> None:
    await as_user("customer")
    fake = use_llm(app, FakeLLM([FakeLLM.text("ok")]))

    await say(client, await new_chat(client), "hi")

    offered = {tool["function"]["name"] for tool in fake.calls[0][1]}
    assert offered == {"get_my_bill_status", "get_my_area_status"}


async def test_invented_staff_tool_call_is_refused(
    app: FastAPI, client: AsyncClient, as_user: AsUser
) -> None:
    """The model may ask for any tool; the registry decides, not the model."""
    await as_user("customer")
    fake = use_llm(
        app,
        FakeLLM(
            [
                FakeLLM.tool("lookup_customer_bills", {"customer_code": "ND-000001"}),
                FakeLLM.text("I can't look that up."),
            ]
        ),
    )

    response = await say(client, await new_chat(client), "show ND-000001's bill")

    assert response.json()["tools_used"] == [{"name": "lookup_customer_bills", "ok": False}]
    tool_reply = next(m for m in fake.calls[1][0] if m["role"] == "tool")
    assert "tool_not_available" in tool_reply["content"]


async def test_stops_after_3_rounds(app: FastAPI, client: AsyncClient, as_user: AsUser) -> None:
    await as_user("customer")
    fake = use_llm(
        app,
        FakeLLM([FakeLLM.tool("get_my_area_status", {}, call_id=f"c{i}") for i in range(3)]),
    )

    response = await say(client, await new_chat(client), "loop forever")

    assert response.status_code == 201
    assert len(fake.calls) == 3
    assert "couldn't finish" in response.json()["content"]


async def test_follow_up_uses_history(app: FastAPI, client: AsyncClient) -> None:
    fake = use_llm(app, FakeLLM([FakeLLM.text("November: ৳1000"), FakeLLM.text("October too")]))
    chat_id = await new_chat(client)

    await say(client, chat_id, "What is my bill?")
    await say(client, chat_id, "And last month?")

    contents = [m.get("content") for m in fake.calls[1][0]]
    assert "What is my bill?" in contents
    assert "November: ৳1000" in contents
    assert contents[-1] == "And last month?"


async def test_only_the_last_12_messages_are_sent(
    app: FastAPI, client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    fake = use_llm(app, FakeLLM([FakeLLM.text("ok")]))
    chat_id = await new_chat(client)
    start = datetime.now(UTC) - timedelta(hours=3)
    db_session.add_all(
        ChatMessage(
            session_id=chat_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"old {i}",
            created_at=start + timedelta(minutes=i),
        )
        for i in range(20)
    )
    await db_session.flush()

    await say(client, chat_id, "new")

    sent = fake.calls[0][0]
    history = [m for m in sent if m["role"] in ("user", "assistant")]
    assert len(history) == 13  # 12 earlier messages + the new one
    assert history[0]["content"] == "old 8"
    assert "NO_EVIDENCE" in sent[0]["content"]  # one system message, then history


async def test_31st_message_of_the_day_is_429(
    app: FastAPI, client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    # Earlier today but over a minute ago, so the per-minute limit does not fire first.
    earlier = max(day_start(datetime.now(UTC)), datetime.now(UTC) - timedelta(minutes=5))
    await add_user_messages(db_session, customer, 30, earlier)
    use_llm(app, FakeLLM([]))

    response = await say(client, await new_chat(client), "one more")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "quota_exceeded"
    assert int(response.headers["Retry-After"]) > 0


async def test_usage_shows_messages_left_before_any_message(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    """The assistant page can show the count on load, not only after the first reply."""
    customer = await as_user("customer")
    earlier = max(day_start(datetime.now(UTC)), datetime.now(UTC) - timedelta(minutes=5))
    await add_user_messages(db_session, customer, 2, earlier)

    response = await client.get("/api/v1/chat/usage")

    assert response.status_code == 200
    assert response.json() == {"messages_left_today": 28, "daily_limit": 30}


async def test_usage_never_goes_below_zero(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    earlier = max(day_start(datetime.now(UTC)), datetime.now(UTC) - timedelta(minutes=5))
    await add_user_messages(db_session, customer, 31, earlier)

    response = await client.get("/api/v1/chat/usage")

    assert response.json()["messages_left_today"] == 0


async def test_seventh_message_in_a_minute_is_429(
    app: FastAPI, client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    await add_user_messages(db_session, customer, 6, datetime.now(UTC) - timedelta(seconds=5))
    use_llm(app, FakeLLM([]))

    response = await say(client, await new_chat(client), "fast")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


async def test_staff_get_the_staff_quota(app: FastAPI, client: AsyncClient) -> None:
    use_llm(app, FakeLLM([FakeLLM.text("ok")]))

    response = await say(client, await new_chat(client), "hi")

    assert response.json()["messages_left_today"] == 99


async def test_global_cap_is_429(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_daily_limit_global", 0)
    use_llm(app, FakeLLM([]))

    response = await say(client, await new_chat(client), "hi")

    assert response.status_code == 429


async def test_kill_switch_gives_503(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_enabled", False)
    use_llm(app, FakeLLM([]))

    response = await say(client, await new_chat(client), "hi")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "chat_disabled"


async def test_model_failure_is_503_and_saves_nothing(
    app: FastAPI, client: AsyncClient, db_session: AsyncSession
) -> None:
    use_llm(app, FakeLLM([], fail=True))
    chat_id = await new_chat(client)

    response = await say(client, chat_id, "hi")
    saved = await db_session.scalar(select(func.count()).select_from(ChatMessage))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_unavailable"
    assert saved == 0  # the failed turn does not count against the quota


async def test_another_users_session_is_404(
    app: FastAPI, client: AsyncClient, as_user: AsUser
) -> None:
    use_llm(app, FakeLLM([]))
    chat_id = await new_chat(client)
    await as_user("customer")

    messages = await client.get(f"/api/v1/chat/sessions/{chat_id}/messages")
    posted = await say(client, chat_id, "hi")
    deleted = await client.delete(f"/api/v1/chat/sessions/{chat_id}")

    assert messages.status_code == posted.status_code == deleted.status_code == 404


async def test_delete_is_soft(client: AsyncClient, db_session: AsyncSession) -> None:
    chat_id = await new_chat(client)

    deleted = await client.delete(f"/api/v1/chat/sessions/{chat_id}")
    listed = await client.get("/api/v1/chat/sessions")
    row = await db_session.get(ChatSession, chat_id)

    assert deleted.status_code == 204
    assert listed.json() == []
    assert row is not None and row.deleted_at is not None  # kept as the audit trail


async def test_messages_endpoint_lists_the_conversation(app: FastAPI, client: AsyncClient) -> None:
    use_llm(app, FakeLLM([FakeLLM.text("answer")]))
    chat_id = await new_chat(client)
    await say(client, chat_id, "question")

    messages = (await client.get(f"/api/v1/chat/sessions/{chat_id}/messages")).json()

    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "question"),
        ("assistant", "answer"),
    ]


async def test_message_over_1000_characters_is_422(client: AsyncClient) -> None:
    response = await say(client, await new_chat(client), "x" * 1001)

    assert response.status_code == 422


async def test_provider_extra_on_a_tool_call_is_echoed_back(
    app: FastAPI, client: AsyncClient, as_user: AsUser
) -> None:
    """Gemini 3 rejects the follow-up call unless each tool call's thought_signature
    (extra_content) is sent back unchanged."""
    await as_user("customer")
    signed = FakeLLM.tool("get_my_area_status", {})
    call = replace(signed.tool_calls[0], extra={"google": {"thought_signature": "sig-1"}})
    fake = use_llm(app, FakeLLM([replace(signed, tool_calls=[call]), FakeLLM.text("done")]))

    await say(client, await new_chat(client), "is my net down?")

    echoed = next(m for m in fake.calls[1][0] if m.get("tool_calls"))
    assert echoed["tool_calls"][0]["extra_content"] == {"google": {"thought_signature": "sig-1"}}
