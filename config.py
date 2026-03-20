# ============================================================
# config.py — all settings in one place, never touch other files to change these
# ============================================================

from dotenv import load_dotenv
import os

load_dotenv()  # reads .env file into environment variables

# ── GPUs to search for on Newegg ─────────────────────────────────────────────
SEARCH_QUERIES = ["3090", "3080", "4090"]       # each becomes a separate Newegg search

# ── Price drop alert threshold ───────────────────────────────────────────────
ALERT_THRESHOLD_PERCENT = 5                     # alert if price drops by 5% or more

# ── How often to re-scrape (in hours) ────────────────────────────────────────
CHECK_INTERVAL_HOURS = 6

# ── Storage ──────────────────────────────────────────────────────────────────
DB_PATH = "data/prices.db"                      # SQLite database file (auto-created on first run)

# ── Email alerts (loaded from .env) ───────────────────────────────────────────────
EMAIL_ENABLED  = os.getenv("EMAIL_ENABLED", "False") == "True"
EMAIL_SENDER   = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")
SMTP_HOST      = "smtp.gmail.com"               # not secret
SMTP_PORT      = 587                            # not secret
