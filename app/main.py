# app/main.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
from contextlib import asynccontextmanager
from datetime import datetime
import os

from app.db import (
    create_db_and_tables, get_async_session,
    GPUPrice, PriceAlert, User, UserSettings, async_session
)
from app.schemas import GPUPriceResponse, PriceAlertResponse
from app.scraper import scrape_all
from app.alerts import check_for_drops
from app.scoring import score_drop, grade
from app.config import SEARCH_QUERIES
from app.routers import auth as auth_router
from app.auth import get_current_user
from app.routers import settings as settings_router
from app.scheduler import start_scheduler, scheduler

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    os.getenv("FRONTEND_URL", "https://gpupricetracker-ftjfijjis-alireza-s-projects5.vercel.app"),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    await start_scheduler()
    yield
    scheduler.shutdown()
    print("[scheduler] Stopped")


app = FastAPI(
    title="GPU Price Tracker",
    description="Tracks GPU prices across retailers and alerts on drops",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(settings_router.router)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Scrape (manual trigger) ───────────────────────────────────────────────────

@app.post("/scrape", status_code=202)
@limiter.limit("5/minute")
async def trigger_scrape(
    request: Request,
    background_tasks: BackgroundTasks,
    queries: list[str] = SEARCH_QUERIES,
):
    """Manually trigger a scrape. The scheduler handles automatic scraping."""
    background_tasks.add_task(run_scrape_cycle, queries)
    return {"detail": f"Scrape started for: {queries}"}


async def run_scrape_cycle(queries: list[str] | None = None):
    import asyncio
    from sqlalchemy import func
    try:
        async with async_session() as session:
            users_result = await session.execute(select(User))
            users = users_result.scalars().all()

            if not users:
                print("[scrape] No users registered yet")
                return

            all_queries: set[str] = set(queries or SEARCH_QUERIES)
            user_settings_map: dict[str, UserSettings] = {}

            for user in users:
                settings_result = await session.execute(
                    select(UserSettings).where(UserSettings.user_id == user.id)
                )
                user_settings = settings_result.scalars().first()
                user_settings_map[user.id] = user_settings
                if user_settings and user_settings.search_queries:
                    user_queries = [q.strip() for q in user_settings.search_queries.split(",") if q.strip()]
                    all_queries.update(user_queries)

        print(f"[scrape] Running with queries: {sorted(all_queries)}")

        loop = asyncio.get_event_loop()
        current = await loop.run_in_executor(None, scrape_all, list(all_queries))
        print(f"[scrape] Scraped {len(current)} items")

        async with async_session() as session:
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
            previous = {
                row.name: {"price": row.price, "link": row.link, "retailer": row.retailer}
                for row in prev_rows
            }

            history_result = await session.execute(
                select(GPUPrice).order_by(GPUPrice.name, GPUPrice.scraped_at.asc())
            )
            history_rows = history_result.scalars().all()
            price_history: dict[str, list[float]] = {}
            for row in history_rows:
                price_history.setdefault(row.name, []).append(row.price)

            for item in current:
                if not item.get("name") or not item.get("price"):
                    continue
                session.add(GPUPrice(
                    name     = item["name"],
                    price    = item["price"],
                    currency = item.get("currency", "USD"),
                    link     = item.get("link"),
                    query    = item.get("query"),
                    retailer = item.get("retailer", "unknown"),
                ))
            await session.commit()

            for user in users:
                user_settings = user_settings_map.get(user.id)

                user_queries = set(SEARCH_QUERIES)
                if user_settings and user_settings.search_queries:
                    user_queries = {q.strip() for q in user_settings.search_queries.split(",") if q.strip()}

                user_current = [
                    item for item in current
                    if item.get("query") in user_queries
                ]

                drops = check_for_drops(
                    previous      = previous,
                    current       = user_current,
                    settings      = user_settings,
                    user_email    = user.email,
                    price_history = price_history,
                )

                for drop in drops:
                    existing = await session.execute(
                        select(PriceAlert).where(
                            PriceAlert.user_id   == user.id,
                            PriceAlert.gpu_name  == drop["name"],
                            PriceAlert.new_price == drop["new_price"],
                        ).limit(1)
                    )
                    if existing.scalars().first():
                        print(f"[scrape] Skipping duplicate alert for {drop['name']} @ ${drop['new_price']}")
                        continue

                    session.add(PriceAlert(
                        user_id   = user.id,
                        gpu_name  = drop["name"],
                        retailer  = drop.get("retailer", "unknown"),
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


# ── Prices ────────────────────────────────────────────────────────────────────

@app.get("/prices", response_model=list[GPUPriceResponse])
async def get_latest_prices(
    query:    str | None = None,
    retailer: str | None = None,
    limit:    int        = Query(default=50, ge=1, le=200),
    cursor:   str | None = Query(default=None, description="scraped_at timestamp from last result, ISO format"),
    session:  AsyncSession = Depends(get_async_session),
):
    stmt = select(GPUPrice).order_by(GPUPrice.scraped_at.desc())
    if query:
        stmt = stmt.where(GPUPrice.query == query)
    if retailer:
        stmt = stmt.where(GPUPrice.retailer == retailer)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            stmt = stmt.where(GPUPrice.scraped_at < cursor_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format. Use ISO datetime.")

    result = await session.execute(stmt)
    prices = result.scalars().all()

    seen, latest = set(), []
    for p in prices:
        if p.name not in seen:
            seen.add(p.name)
            latest.append(p)
        if len(latest) >= limit:
            break

    if not latest:
        return []

    history_result = await session.execute(
        select(GPUPrice).order_by(GPUPrice.name, GPUPrice.scraped_at.asc())
    )
    history_rows = history_result.scalars().all()
    price_history: dict[str, list[float]] = {}
    for row in history_rows:
        price_history.setdefault(row.name, []).append(row.price)

    all_current = [{"name": p.name, "price": p.price} for p in latest]

    output = []
    for p in latest:
        history = price_history.get(p.name, [p.price])
        historical_high = max(history) if history else p.price
        drop_pct = (
            ((historical_high - p.price) / historical_high) * 100
            if historical_high > p.price else 0.0
        )
        s = score_drop(
            drop_pct      = drop_pct,
            price_history = history,
            current_price = p.price,
            all_current   = all_current,
            gpu_name      = p.name,
        )
        g = grade(s)
        output.append(GPUPriceResponse(
            id         = p.id,
            name       = p.name,
            price      = p.price,
            currency   = p.currency,
            link       = p.link,
            query      = p.query,
            retailer   = p.retailer,
            scraped_at = p.scraped_at,
            score      = s,
            grade      = g,
        ))

    output.sort(key=lambda x: x.score or 0, reverse=True)
    return output


@app.get("/prices/history", response_model=list[GPUPriceResponse])
async def get_price_history(
    name:    str,
    limit:   int        = Query(default=100, ge=1, le=500),
    cursor:  str | None = Query(default=None, description="scraped_at timestamp from last result, ISO format"),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = (
        select(GPUPrice)
        .where(GPUPrice.name == name)
        .order_by(GPUPrice.scraped_at.asc())
    )
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            stmt = stmt.where(GPUPrice.scraped_at > cursor_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format. Use ISO datetime.")

    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    history = result.scalars().all()
    if not history:
        raise HTTPException(status_code=404, detail="No price history found for that product")
    return history


# ── Alerts ────────────────────────────────────────────────────────────────────

@app.get("/alerts", response_model=list[PriceAlertResponse])
async def get_alerts(
    limit:        int        = Query(default=50, ge=1, le=200),
    cursor:       str | None = Query(default=None, description="created_at timestamp from last result, ISO format"),
    session:      AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(PriceAlert)
        .where(PriceAlert.user_id == current_user.id)
        .order_by(desc(PriceAlert.score), desc(PriceAlert.created_at))
    )
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            stmt = stmt.where(PriceAlert.created_at < cursor_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format. Use ISO datetime.")

    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()