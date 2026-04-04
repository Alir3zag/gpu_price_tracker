# ============================================================
# scheduler.py — APScheduler integration
#
# Runs a scrape job for every user automatically, each on their
# own check_interval_hours. Jobs are registered on startup and
# self-update: every time a job fires it re-reads the user's
# current settings and reschedules itself if the interval changed.
# ============================================================

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
import asyncio

from app.db import async_session, User, UserSettings, GPUPrice, PriceAlert
from app.scraper import scrape_all
from app.alerts import check_for_drops

# One global scheduler instance — created here, started in main.py lifespan
scheduler = AsyncIOScheduler()


# ── Core scrape job ───────────────────────────────────────────────────────────

async def scrape_for_user(user_id: str) -> None:
    """Full scrape + alert cycle for a single user.

    1. Load user + settings from DB
    2. Scrape their configured queries
    3. Fetch previous prices BEFORE inserting new ones
    4. Fetch full price history for the scorer
    5. Save new prices with correct retailer field
    6. Check for drops, score them, save alerts
    7. Reschedule own job if interval has changed
    """
    async with async_session() as session:
        # ── 1. Load user + settings ──────────────────────────────────────────
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalars().first()
        if not user:
            # User was deleted — remove their job and bail
            job_id = f"scrape_user_{user_id}"
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            return

        settings_result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = settings_result.scalars().first()
        if not settings:
            print(f"[scheduler] No settings found for user {user_id}, skipping")
            return

        queries       = [q.strip() for q in settings.search_queries.split(",") if q.strip()]
        interval_hrs  = settings.check_interval_hours
        print(f"[scheduler] Running scrape for {user.email} | queries={queries} | interval={interval_hrs}h")

        # ── 2. Scrape ────────────────────────────────────────────────────────
        # scrape_all is a sync function — run it in a thread so it doesn't
        # block the event loop while making HTTP requests
        loop = asyncio.get_event_loop()
        current = await loop.run_in_executor(None, scrape_all, queries)
        print(f"[scheduler] Scraped {len(current)} items for {user.email}")

        if not current:
            print(f"[scheduler] No results for {user.email}, skipping save")
            return

        # ── 3. fetch previous prices BEFORE inserting ────────────────────
        from sqlalchemy import func
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

        # ── 4. fetch full price history for scorer ───────────────────────
        history_result = await session.execute(
            select(GPUPrice).order_by(GPUPrice.name, GPUPrice.scraped_at.asc())
        )
        history_rows = history_result.scalars().all()
        price_history: dict[str, list[float]] = {}
        for row in history_rows:
            price_history.setdefault(row.name, []).append(row.price)

        # ── 5. Save raw prices with correct retailer ─────────────────────
        for item in current:
            if not item.get("name") or not item.get("price"):
                continue
            session.add(GPUPrice(
                name     = item["name"],
                price    = item["price"],
                link     = item.get("link"),
                query    = item.get("query"),
                retailer = item.get("retailer", "unknown"),  # ← fixed
            ))
        await session.commit()

        # ── 6. Check for drops and save alerts ───────────────────────────
        drops = check_for_drops(
            previous      = previous,
            current       = current,
            settings      = settings,
            user_email    = user.email,
            price_history = price_history,   # ← new
        )
        for drop in drops:
            session.add(PriceAlert(
                user_id   = user_id,
                gpu_name  = drop["name"],
                old_price = drop["old_price"],
                new_price = drop["new_price"],
                drop_pct  = drop["drop_pct"],
                score     = drop["score"],   # ← new
                grade     = drop["grade"],   # ← new
                link      = drop["link"],
            ))
        await session.commit()


# ── Registration helpers ──────────────────────────────────────────────────────

def register_user_job(user_id: str, interval_hours: float) -> None:
    """Add a recurring scrape job for one user.

    Safe to call even if the job already exists — replaces the old one.
    Called from:
    - start_scheduler() on app startup (for all existing users)
    - POST /auth/register (for new users, so they start scraping immediately)
    """
    job_id = f"scrape_user_{user_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)    # replace cleanly rather than duplicate

    scheduler.add_job(
        scrape_for_user,
        trigger=IntervalTrigger(hours=interval_hours),
        args=[user_id],
        id=job_id,
        name=f"Scrape job for user {user_id}",
        replace_existing=True,
        max_instances=1,        # never run two scrapes for the same user at once
    )
    print(f"[scheduler] Job registered for user {user_id} every {interval_hours}h")


def remove_user_job(user_id: str) -> None:
    """Remove a user's scrape job. Call this if a user deletes their account."""
    job_id = f"scrape_user_{user_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"[scheduler] Job removed for user {user_id}")


# ── Startup ───────────────────────────────────────────────────────────────────

async def start_scheduler() -> None:
    """Load all users from DB and register a scrape job for each one.

    Called from main.py lifespan on app startup. Starts the APScheduler
    instance then seeds it with one job per existing user.

    New users registered after startup get their job added immediately
    via register_user_job() called from the /auth/register endpoint.
    """
    scheduler.start()
    print("[scheduler] Started")

    async with async_session() as session:
        result = await session.execute(select(User))
        users  = result.scalars().all()

    for user in users:
        # Load each user's settings to get their interval
        async with async_session() as session:
            settings_result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user.id)
            )
            settings = settings_result.scalars().first()

        interval = settings.check_interval_hours if settings else 6.0
        register_user_job(user.id, interval)

    print(f"[scheduler] {len(users)} job(s) registered on startup")
