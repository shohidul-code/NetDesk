"""POST /auth/register: a customer claims the connection their ISP already created
(PROPOSAL §6.10)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import make_connection, make_user

URL = "/api/v1/auth/register"
PHONE = "+8801712345678"
PASSWORD = "a-long-enough-password"


def _body(code: str, **kw: object) -> dict[str, object]:
    body: dict[str, object] = {
        "customer_code": code,
        "phone": "01712-345678",  # accepted in local form, stored as E.164
        "email": "New.Customer@Example.test",
        "password": PASSWORD,
    }
    return {**body, **kw}


async def test_register_links_the_connection_and_the_user_can_log_in(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session, phone=PHONE)

    response = await client.post(URL, json=_body(connection.customer_code))

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.customer@example.test"  # lower-cased
    assert body["role"] == "customer"
    assert body["full_name"] == connection.customer_name
    assert "password" not in response.text
    await db_session.refresh(connection)
    assert str(connection.customer_user_id) == body["id"]
    login = await client.post(
        "/api/v1/auth/login", data={"username": "new.customer@example.test", "password": PASSWORD}
    )
    assert login.status_code == 200


async def test_wrong_phone_is_404(client: AsyncClient, db_session: AsyncSession) -> None:
    connection = await make_connection(db_session, phone=PHONE)

    response = await client.post(URL, json=_body(connection.customer_code, phone="01812345678"))

    assert response.status_code == 404
    assert response.json()["error"]["message"] == (
        "No connection matches this customer code and phone."
    )


async def test_unknown_customer_code_is_404(client: AsyncClient) -> None:
    response = await client.post(URL, json=_body("ND-999999"))

    assert response.status_code == 404


async def test_already_claimed_connection_is_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session, "customer")
    connection = await make_connection(db_session, phone=PHONE, customer_user_id=owner.id)

    response = await client.post(URL, json=_body(connection.customer_code))

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "This connection is already claimed."


async def test_email_already_registered_is_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    taken = await make_user(db_session, "customer")
    connection = await make_connection(db_session, phone=PHONE)

    response = await client.post(URL, json=_body(connection.customer_code, email=taken.email))

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "This email is already registered."
    await db_session.refresh(connection)
    assert connection.customer_user_id is None


@pytest.mark.parametrize(
    "change",
    [
        {"password": "short"},
        {"password": "x" * 129},
        {"email": "not-an-email"},
        {"customer_code": "ND-12"},
        {"phone": "12345"},
        {"role": "admin"},  # extra fields are rejected, not ignored
    ],
)
async def test_invalid_input_is_422_and_never_echoed(
    client: AsyncClient, change: dict[str, object]
) -> None:
    response = await client.post(URL, json=_body("ND-000001", **change))

    assert response.status_code == 422
    assert PASSWORD not in response.text
