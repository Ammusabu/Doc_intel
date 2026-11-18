"""Auth tests. Real DB, real HTTP flow. Per-loop engine isolates each test."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac


def _rand_email(prefix: str = "test_user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


@pytest.mark.asyncio
async def test_register_returns_user(client):
    email = _rand_email()
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd!", "full_name": "Test User",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == email.lower()
    assert body["full_name"] == "Test User"
    assert "id" in body
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client):
    email = _rand_email()
    r1 = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd!", "full_name": "A",
    })
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd!", "full_name": "B",
    })
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_login_success_returns_jwt(client):
    email = _rand_email()
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd!", "full_name": "Login User",
    })
    r = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "Passw0rd!",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == email.lower()


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client):
    email = _rand_email()
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "CorrectPass1!", "full_name": "X",
    })
    r = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "WrongPass1!",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token(client):
    email = _rand_email()
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Passw0rd!", "full_name": "Me User",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "Passw0rd!",
    })
    token = login.json()["access_token"]
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == email.lower()


@pytest.mark.asyncio
async def test_me_without_token_rejected(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
