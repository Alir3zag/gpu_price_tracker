# ============================================================
# config.py — all settings in one place, never touch other files to change these
# ============================================================

from dotenv import load_dotenv
load_dotenv()  # reads .env file into environment variables
import os


# API keys for external services — set these in a .env file in the project root
BESTBUY_API_KEY    = os.getenv("BESTBUY_API_KEY", "")
EBAY_CLIENT_ID     = os.getenv("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET", "")
SCRAPERAPI_KEY     = os.getenv("SCRAPERAPI_KEY", "")


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

# ── Auth ─────────────────────────────────────────────────────────────────────
JWT_SECRET     = os.getenv("JWT_SECRET", "changeme-before-deploy")  # sign/verify tokens
JWT_ALGORITHM  = "HS256"          # hashing algorithm used to sign the token
JWT_EXPIRE_MIN = 60 * 24          # token lives for 24 hours