# tests/test_alerts.py
import pytest
from app.alerts import check_for_drops

pytestmark = pytest.mark.asyncio


# ── Unit tests for check_for_drops ───────────────────────────────────────────

def test_drop_detected_above_threshold():
    previous = {"RTX 3080": {"price": 700.0, "link": "https://example.com", "retailer": "newegg"}}
    current  = [{"name": "RTX 3080", "price": 560.0, "link": "https://example.com", "retailer": "newegg"}]
    drops = check_for_drops(previous=previous, current=current)
    assert len(drops) == 1
    assert drops[0]["name"] == "RTX 3080"
    assert drops[0]["drop_pct"] == pytest.approx(20.0, rel=0.01)


def test_no_drop_below_threshold():
    previous = {"RTX 3080": {"price": 700.0, "link": "", "retailer": "newegg"}}
    current  = [{"name": "RTX 3080", "price": 697.0, "link": "", "retailer": "newegg"}]  # <5% drop
    drops = check_for_drops(previous=previous, current=current)
    assert len(drops) == 0


def test_price_increase_ignored():
    previous = {"RTX 3080": {"price": 600.0, "link": "", "retailer": "newegg"}}
    current  = [{"name": "RTX 3080", "price": 650.0, "link": "", "retailer": "newegg"}]
    drops = check_for_drops(previous=previous, current=current)
    assert len(drops) == 0


def test_new_gpu_not_in_previous_ignored():
    previous = {}
    current  = [{"name": "RTX 4090", "price": 1999.0, "link": "", "retailer": "newegg"}]
    drops = check_for_drops(previous=previous, current=current)
    assert len(drops) == 0


def test_drop_uses_lowest_current_price():
    """When same GPU appears from multiple retailers, alert uses the lowest price."""
    previous = {"RTX 3080": {"price": 700.0, "link": "", "retailer": "newegg"}}
    current  = [
        {"name": "RTX 3080", "price": 650.0, "link": "", "retailer": "newegg"},
        {"name": "RTX 3080", "price": 580.0, "link": "", "retailer": "walmart"},
    ]
    drops = check_for_drops(previous=previous, current=current)
    assert len(drops) == 1
    assert drops[0]["new_price"] == 580.0


def test_deduplication_one_alert_per_gpu():
    previous = {
        "RTX 3080": {"price": 700.0, "link": "", "retailer": "newegg"},
    }
    current = [
        {"name": "RTX 3080", "price": 500.0, "link": "", "retailer": "newegg"},
        {"name": "RTX 3080", "price": 490.0, "link": "", "retailer": "walmart"},
    ]
    drops = check_for_drops(previous=previous, current=current)
    assert len(drops) == 1


def test_custom_threshold_respected():
    previous = {"RTX 3080": {"price": 700.0, "link": "", "retailer": "newegg"}}
    current  = [{"name": "RTX 3080", "price": 665.0, "link": "", "retailer": "newegg"}]  # ~5% drop

    class MockSettings:
        alert_threshold = 10.0  # require 10%
        email_enabled = False

    drops = check_for_drops(previous=previous, current=current, settings=MockSettings())
    assert len(drops) == 0  # 5% < 10% threshold, no alert


def test_drop_has_score_and_grade():
    previous = {"RTX 3080": {"price": 800.0, "link": "", "retailer": "newegg"}}
    current  = [{"name": "RTX 3080", "price": 560.0, "link": "", "retailer": "newegg"}]
    drops = check_for_drops(previous=previous, current=current)
    assert len(drops) == 1
    assert "score" in drops[0]
    assert "grade" in drops[0]
    assert drops[0]["grade"] in ["A", "B", "C", "D"]
    assert 0 <= drops[0]["score"] <= 100


# ── Integration tests for /alerts endpoint ────────────────────────────────────

async def test_alerts_requires_auth(client):
    resp = await client.get("/alerts")
    assert resp.status_code == 401


async def test_alerts_empty_for_new_user(auth_client):
    resp = await auth_client.get("/alerts")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_alerts_isolated_per_user(client):
    """Two users should not see each other's alerts."""
    # Register user A
    await client.post("/auth/register", json={"email": "a@example.com", "password": "pass123"})
    resp_a = await client.post("/auth/login", data={"username": "a@example.com", "password": "pass123"})
    token_a = resp_a.json()["access_token"]

    # Register user B
    await client.post("/auth/register", json={"email": "b@example.com", "password": "pass123"})
    resp_b = await client.post("/auth/login", data={"username": "b@example.com", "password": "pass123"})
    token_b = resp_b.json()["access_token"]

    # Both users start with 0 alerts
    client.headers["Authorization"] = f"Bearer {token_a}"
    assert (await client.get("/alerts")).json() == []

    client.headers["Authorization"] = f"Bearer {token_b}"
    assert (await client.get("/alerts")).json() == []
