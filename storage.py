# ============================================================
# storage.py — SQLite database: save prices, load latest, fetch history
# ============================================================

import sqlite3
import os
from datetime import datetime
from config import DB_PATH


def _connect() -> sqlite3.Connection:
    """Open (or create) the SQLite DB and ensure the prices table exists."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)    # create data folder if missing
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row                          # rows behave like dicts
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            price     REAL    NOT NULL,
            link      TEXT,
            query     TEXT,
            scraped_at TEXT   NOT NULL                      -- ISO timestamp of this scrape
        )
    """)
    conn.commit()
    return conn


def save_prices(items: list[dict]) -> None:
    """Insert a fresh batch of scraped items into the database."""
    conn = _connect()
    now  = datetime.now().isoformat()

    conn.executemany(
        "INSERT INTO prices (name, price, link, query, scraped_at) VALUES (:name, :price, :link, :query, :scraped_at)",
        [{**item, "scraped_at": now} for item in items],    # add timestamp
    )
    conn.commit()
    conn.close()
    print(f"[storage] Saved {len(items)} items at {now}")


def load_latest_prices() -> dict[str, dict]:
    """Return the most recent price for each product name as {name: {price, link}}."""
    conn  = _connect()
    # subquery picks the latest scraped_at per product name
    rows  = conn.execute("""
        SELECT name, price, link
        FROM prices
        WHERE scraped_at = (
            SELECT MAX(scraped_at) FROM prices AS p2 WHERE p2.name = prices.name
        )
    """).fetchall()
    conn.close()
    return {row["name"]: {"price": row["price"], "link": row["link"]} for row in rows}


def load_price_history(name: str) -> list[dict]:
    """Return full price history for one product, oldest first — useful for charting later."""
    conn = _connect()
    rows = conn.execute(
        "SELECT price, scraped_at FROM prices WHERE name = ? ORDER BY scraped_at ASC",
        (name,)
    ).fetchall()
    conn.close()
    return [{"price": row["price"], "scraped_at": row["scraped_at"]} for row in rows]
