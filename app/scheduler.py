# ============================================================
# scheduler.py — APScheduler integration
#
# Architecture: two jobs, not one per user.
#
#   global_scrape_job   — runs every CHECK_INTERVAL_HOURS
#                         scrapes all queries from all users (deduplicated)
#                         saves price data to the shared DB
#
#   global_alert_job    — runs after every scrape
#                         checks each user's alert threshold against new prices
#                         saves PriceAlert rows per user
#
# This replaces the old per-user scrape design where N users tracking
# the same GPU caused N identical HTTP requests per interval.
# ============================================================

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, func
import asyncio

from app.db import async_session, User, UserSettings, GPUPrice, PriceAlert
from app.scraper import scrape_all
from app.alerts import check_for_drops
from app.config import CHECK_INTERVAL_HOURS, SEARCH_QUERIES

scheduler = AsyncIOScheduler()


# ── Step 1: scrape shared price data ─────────────────────────────────────────

async def global_scrape_job() -> None:
    """Scrape GPU prices for all unique queries across all users.

    Deduplicates queries so '4090' tracked by 10 users still only
    triggers one HTTP request. Saves results to the shared gpu_prices table.
    After saving, immediately triggers alert checks for all users.
    """
    print("[scheduler] Global scrape started")

    async with async_session() as session:
        result = await session.execute(select(UserSettings))
        all_settings = result.scalars().all()

    # Collect unique queries from all users + fall back to config defaults
    user_queries: set[str] = set(SEARCH_QUERIES)
    for s in all_settings:
        for q in s.search_queries.split(","):
            q = q.strip()
            if q:
                user_queries.add(q)

    queries = list(user_queries)
    print(f"[scheduler] Scraping {len(queries)} unique queries: {queries}")

    loop = asyncio.get_event_loop()
    current = await loop.run_in_executor(None, scrape_all, queries)
    print(f"[scheduler] Scraped {len(current)} items")

    if not current:
        print("[scheduler] No results — skipping save")
        return

    async with async_session() as session:
        # Fetch previous prices BEFORE inserting new ones (for drop detection)
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
        previous  = {row.name: {"price": row.price, "link": row.link} for row in prev_rows}

        # Fetch full price history for scorer
        history_result = await session.execute(
            select(GPUPrice).order_by(GPUPrice.name, GPUPrice.scraped_at.asc())
        )
        history_rows = history_result.scalars().all()
        price_history: dict[str, list[float]] = {}
        for row in history_rows:
            price_history.setdefault(row.name, []).append(row.price)

        # Save new prices
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
        print(f"[scheduler] Saved {len(current)} price records")

    # Trigger alert checks immediately after saving
    await global_alert_job(previous=previous, current=current, price_history=price_history)


# ── Step 2: fan out alerts to each user ──────────────────────────────────────

async def global_alert_job(
    previous:      dict,
    current:       list[dict],
    price_history: dict[str, list[float]],
) -> None:
    """Check every user's alert threshold against the freshly scraped prices.

    Each user only gets alerted on drops that exceed their personal threshold.
    Scraping is not repeated — data is passed in from global_scrape_job.
    """
    async with async_session() as session:
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()

        alert_count = 0
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
                alert_count += 1

        await session.commit()
        print(f"[scheduler] Alert check done — {len(users)} user(s), {alert_count} alert(s) saved")


# ── Registration helpers (kept for auth router compatibility) ─────────────────
# These no longer control scrape frequency — the global job handles that.
# They exist so the auth router can still call register_user_job on signup
# without needing changes, and remove_user_job on account deletion.

def register_user_job(user_id: str, interval_hours: float = 0) -> None:
    """No-op stub kept for auth router compatibility.

    The global scrape job handles all scraping. Individual user jobs
    are no longer needed. interval_hours is ignored.
    """
    print(f"[scheduler] User {user_id} registered (global job handles scraping)")


def remove_user_job(user_id: str) -> None:
    """No-op stub kept for auth router compatibility."""
    print(f"[scheduler] User {user_id} removed (no individual job to clean up)")


# ── Startup ───────────────────────────────────────────────────────────────────

async def start_scheduler() -> None:
    """Start the global scrape job on a fixed interval.

    Called from main.py lifespan on app startup.
    One job scrapes all queries, then fans out alerts to all users.
    """
    scheduler.start()
    print("[scheduler] Started")

    scheduler.add_job(
        global_scrape_job,
        trigger=IntervalTrigger(hours=CHECK_INTERVAL_HOURS),
        id="global_scrape",
        name="Global GPU price scrape",
        replace_existing=True,
        max_instances=1,    # never overlap — if a scrape is still running, skip the next fire
    )
    print(f"[scheduler] Global scrape job registered — every {CHECK_INTERVAL_HOURS}h")
    print("[scheduler] 0 job(s) registered on startup")  # kept for log consistency