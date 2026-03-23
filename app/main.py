# app/main.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from contextlib import asynccontextmanager

from app.db import create_db_and_tables, get_async_session, GPUPrice, PriceAlert
from app.schemas import GPUPriceResponse, PriceAlertResponse, UserSettingsUpdate
from app.scraper import scrape_all
from app.storage import save_prices, load_latest_prices
from app.config import SEARCH_QUERIES


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()        # create all tables on startup
    yield


app = FastAPI(
    title="GPU Price Tracker",
    description="Tracks GPU prices across retailers and alerts on drops",
    lifespan=lifespan
)


# ── Scrape ────────────────────────────────────────────────────────────────────

@app.post("/scrape", status_code=202)
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    queries: list[str] = SEARCH_QUERIES,
    session: AsyncSession = Depends(get_async_session)
):
    """Manually trigger a scrape. Runs in the background so it doesn't block."""
    background_tasks.add_task(run_scrape_cycle, queries)    # non-blocking
    return {"detail": f"Scrape started for: {queries}"}


async def run_scrape_cycle(queries: list[str]):
    from app.db import async_session, GPUPrice
    from app.scraper import scrape_all

    try:
        current = scrape_all(queries)
        print(f"[scrape] Scraped {len(current)} items")   # check if scraper returns anything

        async with async_session() as session:
            for item in current:
                gpu = GPUPrice(
                    name     = item["name"],
                    price    = item["price"],
                    link     = item["link"],
                    query    = item["query"],
                    retailer = "newegg",
                )
                session.add(gpu)
            await session.commit()
            print(f"[scrape] Saved {len(current)} items to DB")  # confirm save

    except Exception as e:
        print(f"[scrape] ERROR: {e}")           # catch anything silently failing


# ── Prices ────────────────────────────────────────────────────────────────────

@app.get("/prices", response_model=list[GPUPriceResponse])
async def get_latest_prices(
    query:   str | None = None,             # optional filter by search query e.g. "3090"
    session: AsyncSession = Depends(get_async_session)
):
    """Return the most recent price for every product."""
    stmt = (
        select(GPUPrice)
        .order_by(GPUPrice.scraped_at.desc())
    )
    if query:
        stmt = stmt.where(GPUPrice.query == query)  # filter by GPU query if provided

    result = await session.execute(stmt)
    prices = result.scalars().all()

    # deduplicate — keep only the latest entry per product name
    seen = set()
    latest = []
    for p in prices:
        if p.name not in seen:
            seen.add(p.name)
            latest.append(p)

    return latest


@app.get("/prices/history", response_model=list[GPUPriceResponse])
async def get_price_history(
    name:    str,                           # required — product name to look up
    session: AsyncSession = Depends(get_async_session)
):
    """Return full price history for one product, oldest first — for charting."""
    result = await session.execute(
        select(GPUPrice)
        .where(GPUPrice.name == name)
        .order_by(GPUPrice.scraped_at.asc())    # oldest first for charts
    )
    history = result.scalars().all()
    if not history:
        raise HTTPException(status_code=404, detail="No price history found for that product")
    return history


# ── Alerts ────────────────────────────────────────────────────────────────────

@app.get("/alerts", response_model=list[PriceAlertResponse])
async def get_alerts(
    session: AsyncSession = Depends(get_async_session)
):
    """Return all recorded price drop alerts, newest first."""
    result = await session.execute(
        select(PriceAlert).order_by(desc(PriceAlert.created_at))
    )
    return result.scalars().all()