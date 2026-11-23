"""Login 5/min and register 3/min per IP (PROPOSAL §9.8). The counter is reset between
tests by an autouse fixture in conftest.py."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"
WRONG_LOGIN = {"username": "nobody@example.test", "password": "wrong-password-123"}
NO_MATCH = {
    "customer_code": "ND-999999",
    "phone": "01712345678",
    "email": "someone@example.test",
    "password": "a-long-enough-password",
}


async def test_sixth_login_from_one_ip_is_429_with_our_envelope(client: AsyncClient) -> None:
    statuses = [(await client.post(LOGIN, data=WRONG_LOGIN)).status_code for _ in range(5)]
    blocked = await client.post(LOGIN, data=WRONG_LOGIN)

    assert statuses == [401] * 5
    assert blocked.status_code == 429
    error = blocked.json()["error"]
    assert error["code"] == "rate_limited"
    assert error["message"] == "Too many attempts. Please wait and try again."
    assert set(error) == {"code", "message", "details", "request_id"}
    assert int(blocked.headers["Retry-After"]) == 60


async def test_fourth_register_from_one_ip_is_429(client: AsyncClient) -> None:
    statuses = [(await client.post(REGISTER, json=NO_MATCH)).status_code for _ in range(3)]
    blocked = await client.post(REGISTER, json=NO_MATCH)

    assert statuses == [404] * 3
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"


async def test_a_different_ip_is_not_blocked(app: FastAPI, client: AsyncClient) -> None:
    for _ in range(6):
        await client.post(LOGIN, data=WRONG_LOGIN)
    transport = ASGITransport(app=app, client=("10.0.0.2", 123))

    async with AsyncClient(transport=transport, base_url="http://test") as other_ip:
        response = await other_ip.post(LOGIN, data=WRONG_LOGIN)

    assert response.status_code == 401
