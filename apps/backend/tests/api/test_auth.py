from typing import Any

import httpx2 as httpx

from stock_research.main import app
from stock_research.stores.session import get_session


async def test_login_and_me(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": db_context.email, "password": db_context.password},
            )
            assert response.status_code == 200
            token = response.json()["access_token"]

            me = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me.status_code == 200
            assert me.json()["email"] == db_context.email
    finally:
        app.dependency_overrides.clear()


async def test_login_wrong_password(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": db_context.email, "password": "wrong-password"},
            )
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    finally:
        app.dependency_overrides.clear()


async def test_refresh_reuse_detection(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": db_context.email, "password": db_context.password},
            )
            assert login.status_code == 200
            old_refresh_token = login.cookies.get("refresh_token")
            assert old_refresh_token is not None

            first_refresh = await client.post("/api/v1/auth/refresh")
            assert first_refresh.status_code == 200

            reuse = await client.post(
                "/api/v1/auth/refresh",
                headers={"Cookie": f"refresh_token={old_refresh_token}"},
            )
            assert reuse.status_code == 401
            assert reuse.json()["error"]["code"] == "AUTH_SESSION_REVOKED"
    finally:
        app.dependency_overrides.clear()
