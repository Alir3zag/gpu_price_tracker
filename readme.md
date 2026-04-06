# GPU Price Tracker

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-async-D71F00?style=flat&logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite→PostgreSQL-003B57?style=flat&logo=sqlite&logoColor=white)
![JWT](https://img.shields.io/badge/Auth-JWT+bcrypt-000000?style=flat&logo=jsonwebtokens&logoColor=white)
![License](https://img.shields.io/github/license/Alir3zag/gpu_price_tracker?style=flat)
![Last Commit](https://img.shields.io/github/last-commit/Alir3zag/gpu_price_tracker?style=flat)

A production-grade REST API that monitors GPU prices across multiple retailers, stores historical price data, and alerts users when prices drop — scored by deal quality, not just threshold.

---

## Features

- **Multi-retailer scraping** — Newegg (BeautifulSoup), Walmart (ScraperAPI), Amazon (ScraperAPI), eBay (official Browse API), Kleinanzeigen stub (EUR, German residential proxy required), Best Buy stub (business API key required)
- **Smart GPU filtering** — blocklist + allowlist + price range validation eliminates full systems, laptops, and accessories from results
- **Multi-currency support** — USD and EUR prices stored with currency field, separate validation ranges per currency
- **Per-user automation** — APScheduler runs each user's scrape on their own configured interval with zero manual triggers
- **Deal scoring** — every price drop is scored 0–100 and graded A–D across three weighted factors, so the best deals always surface first
- **JWT authentication** — bcrypt password hashing, 24-hour tokens, protected route dependency injection
- **Per-user settings** — individual alert thresholds, search queries, check intervals, and email preferences
- **Price history** — full timeline per product, structured for direct use by charting libraries
- **Email alerts** — optional SMTP notifications with deal grade in the subject line

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Client                           │
│              (HTTP / React Frontend / Extension)        │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                    FastAPI App                          │
│                                                         │
│   /auth        /settings      /scrape                   │
│   /prices      /prices/history         /alerts          │
│                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│   │   Auth   │  │ Settings │  │  Background Scrape   │ │
│   │JWT+bcrypt│  │per-user  │  │  + Alert + Scoring   │ │
│   └──────────┘  └──────────┘  └──────────────────────┘ │
└───────┬───────────────┬────────────────┬────────────────┘
        │               │                │
┌───────▼───────┐ ┌─────▼──────┐ ┌──────▼───────────────────────┐
│  SQLAlchemy   │ │ APScheduler│ │         Scrapers              │
│  Async ORM    │ │ per-user   │ │                               │
│  SQLite →     │ │ intervals  │ │  Newegg        (requests) USD │
│  PostgreSQL   │ └────────────┘ │  Walmart       (ScraperAPI)USD│
└───────────────┘                │  Amazon        (ScraperAPI)USD│
                                 │  eBay          (OAuth2 API)USD│
                                 │  Kleinanzeigen (stub)      EUR│
                                 │  Best Buy      (stub)      USD│
                                 └──────────────────────────────┘
```

---

## Deal Scoring

Every price drop alert is scored using three weighted factors:

| Factor | Weight | Description |
|---|---|---|
| Drop size | 40% | Percentage drop mapped to 0–100. Capped at 30% (anything above is exceptional) |
| Historical rarity | 35% | How the new price compares to the all-time low for that GPU |
| Cross-retailer position | 25% | Whether this is the cheapest the GPU is across all tracked retailers right now |

Scores map to letter grades: **A** (80–100) · **B** (60–79) · **C** (40–59) · **D** (0–39)

Alerts are returned sorted by score descending — best deals always appear first.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy (async) |
| Database | SQLite (dev) → PostgreSQL (production) |
| Auth | JWT (HS256) + bcrypt via passlib |
| Scraping | requests + BeautifulSoup, ScraperAPI (anti-bot layer) |
| Retailer APIs | eBay Browse API (OAuth2), Best Buy Products API (stub) |
| Anti-bot | ScraperAPI — handles Walmart, Amazon, Kleinanzeigen |
| Scheduler | APScheduler (AsyncIOScheduler) |
| Deployment | Railway (backend + PostgreSQL) |

---

## Retailer Status

| Retailer | Method | Currency | Status |
|---|---|---|---|
| Newegg | requests + BeautifulSoup | USD | ✅ Working |
| Walmart | ScraperAPI + `__NEXT_DATA__` JSON | USD | ✅ Working |
| Amazon | ScraperAPI + BeautifulSoup | USD | ✅ Working |
| eBay | Official Browse API (OAuth2) | USD | ✅ Working |
| Kleinanzeigen | ScraperAPI + BeautifulSoup | EUR | ⏳ Needs paid ScraperAPI plan (German residential proxy) |
| Best Buy | Official Products API | USD | ⏳ Needs business email for API key |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Git

### Installation

```bash
git clone https://github.com/Alir3zag/gpu_price_tracker.git
cd gpu_price_tracker

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DB_PATH=data/prices.db

# Auth
JWT_SECRET=your-random-secret-here

# Email alerts (optional)
EMAIL_SENDER=you@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECEIVER=you@gmail.com
EMAIL_ENABLED=false

# Anti-bot layer — sign up free at scraperapi.com (5000 credits/month trial)
SCRAPERAPI_KEY=your-scraperapi-key

# Retailer APIs (optional — scrapers skip gracefully if not set)
EBAY_CLIENT_ID=your-ebay-app-id
EBAY_CLIENT_SECRET=your-ebay-cert-id
BESTBUY_API_KEY=your-bestbuy-api-key
```

### Run

```bash
uvicorn app.main:app --reload
```

API is live at `http://127.0.0.1:8000`  
Interactive docs at `http://127.0.0.1:8000/docs`

---

## API Reference

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Create account — returns user profile |
| POST | `/auth/login` | None | Login — returns JWT access token |
| GET | `/auth/me` | Bearer token | Returns current user profile |

**Register**
```json
POST /auth/register
{
  "email": "you@example.com",
  "password": "yourpassword"
}
```

**Login**
```json
POST /auth/login
{
  "email": "you@example.com",
  "password": "yourpassword"
}

→ { "access_token": "eyJ...", "token_type": "bearer" }
```

---

### Settings

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/settings` | Bearer token | Return current user preferences |
| PATCH | `/settings` | Bearer token | Partial update — only provided fields change |

**Settings fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `email_enabled` | bool | false | Send email alerts on price drops |
| `alert_threshold` | float | 5.0 | Minimum % drop to trigger an alert |
| `check_interval_hours` | float | 6.0 | How often to auto-scrape |
| `search_queries` | list[str] | ["3090","3080","4090"] | GPU models to track |

---

### Prices

| Method | Endpoint | Auth | Query Params | Description |
|---|---|---|---|---|
| POST | `/scrape` | None | — | Manually trigger a scrape (scheduler handles automatic) |
| GET | `/prices` | None | `query`, `retailer` | Latest price per GPU, filterable by retailer |
| GET | `/prices/history` | None | `name` (required) | Full price timeline for one product |

**Filter by retailer:**
```
GET /prices?retailer=newegg
GET /prices?retailer=walmart
GET /prices?retailer=amazon
GET /prices?retailer=ebay
```

**Price history:**
```
GET /prices/history?name=ASUS GeForce RTX 4090 24GB
```

---

### Alerts

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/alerts` | None | All price drop alerts, sorted by deal score descending |

**Alert response includes:**
```json
{
  "id": "uuid",
  "gpu_name": "ASUS GeForce RTX 4090 24GB",
  "old_price": 1199.99,
  "new_price": 949.99,
  "drop_pct": 20.83,
  "score": 86.7,
  "grade": "A",
  "link": "https://www.newegg.com/...",
  "created_at": "2026-04-04T10:22:00"
}
```

---

## Project Structure

```
gpu_price_tracker/
├── app/
│   ├── routers/
│   │   ├── auth.py          # register, login, me
│   │   └── settings.py      # get + patch user settings
│   ├── alerts.py            # drop detection + email notifications
│   ├── config.py            # env var loading
│   ├── db.py                # SQLAlchemy models + async engine
│   ├── main.py              # FastAPI app + price endpoints
│   ├── scheduler.py         # APScheduler per-user scrape jobs
│   ├── schemas.py           # Pydantic request/response models
│   ├── scraper.py           # multi-retailer scrapers + ScraperAPI integration
│   └── scoring.py           # deal quality scorer (0–100 + A–D grade)
├── data/
│   └── prices.db            # SQLite database (dev only, not committed)
├── .env                     # local environment variables (not committed)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Roadmap

- [x] Stage 1 — Data models & database (SQLAlchemy async, SQLite)
- [x] Stage 2 — Newegg scraper
- [x] Stage 3 — JWT authentication
- [x] Stage 4 — Per-user settings
- [x] Stage 5 — APScheduler automation
- [x] Stage 6 — Multi-retailer scraping (Walmart, Amazon, eBay, Kleinanzeigen stub, Best Buy stub)
- [x] Stage 7 — Deal scoring (0–100, A–D grades)
- [ ] Stage 8 — Deployment (Railway + PostgreSQL)
- [ ] Stage 9 — React frontend (Vite + Tailwind + Recharts)
- [ ] Stage 10 — AI + Selenium integration
- [ ] Stage 11 — Chrome Extension (Manifest V3)

---

## License

MIT
