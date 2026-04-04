# app/main.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from contextlib import asynccontextmanager

from app.db import (
    create_db_and_tables, get_async_session,
    GPUPrice, PriceAlert, User, UserSettings, async_session
)
from app.schemas import GPUPriceResponse, PriceAlertResponse
from app.scraper import scrape_all
from app.alerts import check_for_drops
from app.config import SEARCH_QUERIES
from app.routers import auth as auth_router
from app.routers import settings as settings_router
from app.scheduler import start_scheduler, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    await start_scheduler()         # start scheduler on startup
    yield
    scheduler.shutdown()            # clean shutdown when app stops
    print("[scheduler] Stopped")


app = FastAPI(
    title="GPU Price Tracker",
    description="Tracks GPU prices across retailers and alerts on drops",
    lifespan=lifespan
)

app.include_router(auth_router.router)
app.include_router(settings_router.router)


# -- Scrape (manual trigger still available) -----------------------------------

@app.post("/scrape", status_code=202)
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    queries: list[str] = SEARCH_QUERIES,
):
    """Manually trigger a scrape. The scheduler handles automatic scraping."""
    background_tasks.add_task(run_scrape_cycle, queries)
    return {"detail": f"Scrape started for: {queries}"}


async def run_scrape_cycle(queries: list[str]):
    import asyncio
    from sqlalchemy import func
    try:
        loop = asyncio.get_event_loop()
        current = await loop.run_in_executor(None, scrape_all, queries)
        print(f"[scrape] Scraped {len(current)} items")

        async with async_session() as session:
            # ── Step 1: fetch previous prices BEFORE inserting ────────────
            subq = (
                select(GPUPrice.name, func.max(GPUPrice.scraped_at).label("latest"))
                .group_by(GPUPrice.name)
                .subquery()
            )
            prev_result = await session.execute(
                select(GPUPrice).join(
                    subq,
                    (GPUPrice.name == subq.c.name) &
                    (GPUPrice.scraped_at == subq.c.latest)
                )
            )
            prev_rows = prev_result.scalars().all()
            previous  = {
                row.name: {"price": row.price, "link": row.link}
                for row in prev_rows
            }

            # ── Step 2: fetch full price history for scorer ───────────────
            history_result = await session.execute(
                select(GPUPrice).order_by(GPUPrice.name, GPUPrice.scraped_at.asc())
            )
            history_rows = history_result.scalars().all()
            price_history: dict[str, list[float]] = {}
            for row in history_rows:
                price_history.setdefault(row.name, []).append(row.price)

            # ── Step 3: insert new prices with correct retailer ───────────
            for item in current:
                if not item.get("name") or not item.get("price"):
                    continue
                session.add(GPUPrice(
                    name     = item["name"],
                    price    = item["price"],
                    link     = item.get("link"),
                    query    = item.get("query"),
                    retailer = item.get("retailer", "unknown"),
                ))
            await session.commit()

            # ── Step 4: check drops and alert each user ───────────────────
            users_result = await session.execute(select(User))
            users = users_result.scalars().all()

            for user in users:
                settings_result = await session.execute(
                    select(UserSettings).where(UserSettings.user_id == user.id)
                )
                user_settings = settings_result.scalars().first()
                drops = check_for_drops(
                    previous      = previous,
                    current       = current,
                    settings      = user_settings,
                    user_email    = user.email,
                    price_history = price_history,
                )
                for drop in drops:
                    session.add(PriceAlert(
                        user_id   = user.id,
                        gpu_name  = drop["name"],
                        old_price = drop["old_price"],
                        new_price = drop["new_price"],
                        drop_pct  = drop["drop_pct"],
                        score     = drop["score"],
                        grade     = drop["grade"],
                        link      = drop["link"],
                    ))
            await session.commit()
            print(f"[scrape] Done — {len(users)} user(s) checked")

    except Exception as e:
        print(f"[scrape] ERROR: {e}")
        raise

# -- Prices --------------------------------------------------------------------

@app.get("/prices", response_model=list[GPUPriceResponse])
async def get_latest_prices(
    query:    str | None = None,
    retailer: str | None = None,
    session:  AsyncSession = Depends(get_async_session)
):
    stmt = select(GPUPrice).order_by(GPUPrice.scraped_at.desc())
    if query:
        stmt = stmt.where(GPUPrice.query == query)
    if retailer:
        stmt = stmt.where(GPUPrice.retailer == retailer)
    result = await session.execute(stmt)
    prices = result.scalars().all()
    seen, latest = set(), []
    for p in prices:
        if p.name not in seen:
            seen.add(p.name)
            latest.append(p)
    return latest


@app.get("/prices/history", response_model=list[GPUPriceResponse])
async def get_price_history(
    name:    str,
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(GPUPrice).where(GPUPrice.name == name).order_by(GPUPrice.scraped_at.asc())
    )
    history = result.scalars().all()
    if not history:
        raise HTTPException(status_code=404, detail="No price history found for that product")
    return history


# -- Alerts --------------------------------------------------------------------

@app.get("/alerts", response_model=list[PriceAlertResponse])
async def get_alerts(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(PriceAlert).order_by(desc(PriceAlert.score))  # best deals first
    )
    return result.scalars().all()
