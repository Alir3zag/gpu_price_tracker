# tests/test_settings.py
import pytest

pytestmark = pytest.mark.asyncio


async def test_settings_requires_auth(client):
    resp = await client.get("/settings")
    assert resp.status_code == 401


async def test_settings_defaults_on_register(auth_client):
    resp = await auth_client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alert_threshold"] == 5.0
    assert data["check_interval_hours"] == 6.0
    assert data["email_enabled"] == False
    assert "3080" in data["search_queries"] or isinstance(data["search_queries"], list)


async def test_settings_patch_threshold(auth_client):
    resp = await auth_client.patch("/settings", json={"alert_threshold": 10.0})
    assert resp.status_code == 200
    assert resp.json()["alert_threshold"] == 10.0


async def test_settings_patch_partial(auth_client):
    """PATCH should only update provided fields."""
    await auth_client.patch("/settings", json={"alert_threshold": 15.0})
    resp = await auth_client.patch("/settings", json={"check_interval_hours": 12.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["alert_threshold"] == 15.0   # unchanged
    assert data["check_interval_hours"] == 12.0  # updated


async def test_settings_patch_email_enabled(auth_client):
    resp = await auth_client.patch("/settings", json={
        "email_enabled": True,
        "email_address": "test@example.com"
    })
    assert resp.status_code == 200
    assert resp.json()["email_enabled"] == True


async def test_settings_patch_search_queries(auth_client):
    resp = await auth_client.patch("/settings", json={
        "search_queries": ["4090", "4080", "3090"]
    })
    assert resp.status_code == 200
    data = resp.json()
    queries = data["search_queries"]
    assert "4090" in queries
    assert "4080" in queries


async def test_settings_isolated_per_user(client):
    """User A's settings should not affect user B's."""
    await client.post("/auth/register", json={"email": "a@example.com", "password": "pass123"})
    resp_a = await client.post("/auth/login", data={"username": "a@example.com", "password": "pass123"})
    token_a = resp_a.json()["access_token"]

    await client.post("/auth/register", json={"email": "b@example.com", "password": "pass123"})
    resp_b = await client.post("/auth/login", data={"username": "b@example.com", "password": "pass123"})
    token_b = resp_b.json()["access_token"]

    # User A changes threshold to 20
    client.headers["Authorization"] = f"Bearer {token_a}"
    await client.patch("/settings", json={"alert_threshold": 20.0})

    # User B should still have default threshold
    client.headers["Authorization"] = f"Bearer {token_b}"
    resp = await client.get("/settings")
    assert resp.json()["alert_threshold"] == 5.0
