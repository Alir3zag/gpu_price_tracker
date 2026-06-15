# tests/test_auth.py
import pytest

pytestmark = pytest.mark.asyncio


async def test_register_success(client):
    resp = await client.post("/auth/register", json={
        "email": "new@example.com",
        "password": "password123"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "password" not in data  # password never returned


async def test_register_duplicate_email(client):
    payload = {"email": "dupe@example.com", "password": "password123"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


async def test_login_success(client):
    await client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "password123"
    })
    resp = await client.post("/auth/login", data={
        "username": "user@example.com",
        "password": "password123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={
        "email": "user@example.com",
        "password": "correctpassword"
    })
    resp = await client.post("/auth/login", data={
        "username": "user@example.com",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401


async def test_login_nonexistent_user(client):
    resp = await client.post("/auth/login", data={
        "username": "nobody@example.com",
        "password": "password123"
    })
    assert resp.status_code == 401


async def test_me_authenticated(auth_client):
    resp = await auth_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


async def test_me_unauthenticated(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_invalid_token(client):
    client.headers["Authorization"] = "Bearer invalid.token.here"
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
