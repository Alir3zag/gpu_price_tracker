# tests/test_prices.py
import pytest
from datetime import datetime
from app.db import GPUPrice, async_session

pytestmark = pytest.mark.asyncio


async def _seed_prices(session, items):
    """Helper to insert GPU prices directly into test DB."""
    for item in items:
        session.add(GPUPrice(
            name=item["name"],
            price=item["price"],
            currency=item.get("currency", "USD"),
            retailer=item.get("retailer", "newegg"),
            query=item.get("query", "3080"),
            link=item.get("link", "https://example.com"),
        ))
    await session.commit()


async def test_prices_empty(client):
    resp = await client.get("/prices")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_prices_returns_data(client):
    from tests.conftest import TestSession
    async with TestSession() as s:
        await _seed_prices(s, [
            {"name": "ASUS RTX 3080", "price": 699.99, "retailer": "newegg"},
            {"name": "MSI RTX 3090", "price": 999.99, "retailer": "walmart"},
        ])
    resp = await client.get("/prices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = [p["name"] for p in data]
    assert "ASUS RTX 3080" in names
    assert "MSI RTX 3090" in names


async def test_prices_deduplicates_by_name(client):
    """Only the latest price per GPU name should be returned."""
    from tests.conftest import TestSession
    async with TestSession() as s:
        await _seed_prices(s, [
            {"name": "ASUS RTX 3080", "price": 799.99},
            {"name": "ASUS RTX 3080", "price": 699.99},  # same GPU, lower price
        ])
    resp = await client.get("/prices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


async def test_prices_filter_by_retailer(client):
    from tests.conftest import TestSession
    async with TestSession() as s:
        await _seed_prices(s, [
            {"name": "ASUS RTX 3080", "price": 699.99, "retailer": "newegg"},
            {"name": "MSI RTX 3090", "price": 999.99, "retailer": "walmart"},
        ])
    resp = await client.get("/prices?retailer=newegg")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["retailer"] == "newegg" for p in data)


async def test_prices_have_score_and_grade(client):
    from tests.conftest import TestSession
    async with TestSession() as s:
        await _seed_prices(s, [
            {"name": "ASUS RTX 3080", "price": 699.99},
        ])
    resp = await client.get("/prices")
    data = resp.json()
    assert "score" in data[0]
    assert "grade" in data[0]
    assert data[0]["grade"] in ["A", "B", "C", "D"]


async def test_prices_sorted_by_score_desc(client):
    from tests.conftest import TestSession
    async with TestSession() as s:
        await _seed_prices(s, [
            {"name": "RTX 4090", "price": 3999.99},
            {"name": "RTX 3080", "price": 299.99},   # lower price = better score
            {"name": "RTX 3090", "price": 599.99},
        ])
    resp = await client.get("/prices")
    data = resp.json()
    scores = [p["score"] for p in data]
    assert scores == sorted(scores, reverse=True)


async def test_price_history_not_found(client):
    resp = await client.get("/prices/history?name=Nonexistent+GPU")
    assert resp.status_code == 404


async def test_price_history_returns_timeline(client):
    from tests.conftest import TestSession
    async with TestSession() as s:
        await _seed_prices(s, [
            {"name": "ASUS RTX 3080", "price": 799.99},
            {"name": "ASUS RTX 3080", "price": 749.99},
            {"name": "ASUS RTX 3080", "price": 699.99},
        ])
    resp = await client.get("/prices/history?name=ASUS+RTX+3080")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
