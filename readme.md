# GPU Price Tracker

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-003B57?style=flat&logo=postgresql&logoColor=white)
![JWT](https://img.shields.io/badge/Auth-JWT+bcrypt-000000?style=flat&logo=jsonwebtokens&logoColor=white)
![License](https://img.shields.io/github/license/Alir3zag/gpu_price_tracker?style=flat)
![Last Commit](https://img.shields.io/github/last-commit/Alir3zag/gpu_price_tracker?style=flat)

A full-stack GPU price tracker that scrapes Newegg, Walmart, Amazon, and eBay, scores every deal 0–100, and surfaces the best opportunities in a React dashboard — deployed and live.

**Live demo:** [gpupricetracker-ftjfijjis-alireza-s-projects5.vercel.app](https://gpupricetracker-ftjfijjis-alireza-s-projects5.vercel.app)  
**API:** [gpu-tracker-backend.onrender.com/docs](https://gpu-tracker-backend.onrender.com/docs)

---

## Features

- **Multi-retailer scraping** — Newegg (BeautifulSoup), Walmart, Amazon (ScraperAPI), eBay (official Browse API OAuth2)
- **Smart GPU filtering** — blocklist + allowlist + price range validation eliminates laptops, full systems, and accessories
- **Deal scoring** — every listing scored 0–100 across drop size, historical rarity, and cross-retailer position; graded A–D
- **Price history** — full timeline per product, visualized with Recharts line charts in the frontend
- **JWT authentication** — bcrypt password hashing, 24-hour tokens, protected route dependency injection
- **Per-user settings** — individual alert thresholds, search queries, check intervals, email preferences
- **APScheduler automation** — per-user scrape jobs run on configurable intervals with zero manual triggers
- **React dashboard** — dark theme, deal-focused layout, grade badges, alerts chart, price history modal
- **PostgreSQL in production** — SQLite for local dev, asyncpg + PostgreSQL on Render

---

## Architecture

```
┌─────────────────────────────────────────┐
│           React Frontend                │
│   Vite + Tailwind + Recharts            │
│   Vercel (CDN)                          │
└──────────────────┬──────────────────────┘
                   │ REST (JWT)
┌──────────────────▼──────────────────────┐
│              FastAPI Backend            │
│                                         │
│   /auth    /settings    /scrape         │
│   /prices  /prices/history   /alerts    │
│                                         │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ │
│  │  Auth   │ │Scheduler │ │ Scrapers │ │
│  │JWT+bcrypt│ │APScheduler│ │4 retailer│ │
│  └─────────┘ └──────────┘ └──────────┘ │
│                                         │
│         SQLAlchemy Async ORM            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│      PostgreSQL (Render free tier)      │
└─────────────────────────────────────────┘
```

---

## Deal Scoring

Every price is scored 0–100 across three weighted factors:

| Factor | Weight | Description |
|---|---|---|
| Drop size | 40% | % drop mapped to 0–100, capped at 30% |
| Historical rarity | 35% | New price vs all-time low for that GPU |
| Cross-retailer position | 25% | Whether this is the cheapest across all tracked retailers |

Scores map to letter grades: **A** (80–100) · **B** (60–79) · **C** (40–59) · **D** (0–39)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind v4 + Recharts |
| Backend | FastAPI + SQLAlchemy (async) |
| Database | SQLite (dev) → PostgreSQL (production) |
| Auth | JWT (HS256) + bcrypt via passlib |
| Scraping | requests + BeautifulSoup + ScraperAPI |
| Scheduler | APScheduler (AsyncIOScheduler) |
| Deployment | Render (backend + PostgreSQL) + Vercel (frontend) |

---

## Retailer Status

| Retailer | Method | Status |
|---|---|---|
| Newegg | requests + BeautifulSoup | ✅ Live |
| Walmart | ScraperAPI + `__NEXT_DATA__` JSON | ✅ Live |
| Amazon | ScraperAPI + BeautifulSoup | ✅ Live |
| eBay | Official Browse API (OAuth2) | ✅ Live |
| Kleinanzeigen | ScraperAPI + BeautifulSoup | ⏳ Needs residential proxy |
| Best Buy | Official Products API | ⏳ Needs business API key |

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
git clone https://github.com/Alir3zag/gpu_price_tracker.git
cd gpu_price_tracker

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
JWT_SECRET=your-random-secret-here
SCRAPERAPI_KEY=your-scraperapi-key
EMAIL_ENABLED=false
```

```bash
uvicorn app.main:app --reload
# API live at http://127.0.0.1:8000
# Docs at http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App live at http://localhost:5173
```

---

## API Reference

### Auth

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login — returns JWT |
| GET | `/auth/me` | Current user profile |

### Prices

| Method | Endpoint | Description |
|---|---|---|
| POST | `/scrape` | Manually trigger scrape |
| GET | `/prices` | Latest price per GPU (filterable) |
| GET | `/prices/history?name=...` | Full price timeline for one GPU |

### Alerts

| Method | Endpoint | Description |
|---|---|---|
| GET | `/alerts` | Price drop alerts, sorted by score |

### Settings

| Method | Endpoint | Description |
|---|---|---|
| GET | `/settings` | Current user preferences |
| PATCH | `/settings` | Update preferences |

---

## Project Structure

```
gpu_price_tracker/
├── app/
│   ├── routers/
│   │   ├── auth.py          # register, login, me
│   │   └── settings.py      # get + patch user settings
│   ├── alerts.py            # drop detection + email notifications
│   ├── auth.py              # JWT + bcrypt helpers
│   ├── config.py            # env var loading
│   ├── db.py                # SQLAlchemy models + async engine
│   ├── main.py              # FastAPI app + price endpoints
│   ├── scheduler.py         # APScheduler per-user scrape jobs
│   ├── schemas.py           # Pydantic request/response models
│   ├── scraper.py           # multi-retailer scrapers
│   └── scoring.py           # deal scorer (0–100 + A–D grade)
├── frontend/
│   ├── src/
│   │   ├── api/             # axios client + per-resource modules
│   │   ├── components/      # Layout, GradeBadge, Skeleton, Toast
│   │   ├── context/         # AuthContext (JWT + localStorage)
│   │   ├── pages/           # Dashboard, Prices, Alerts, Settings, Login, Register
│   │   └── utils/           # formatters + shortGPUName
│   ├── .env.production
│   └── vercel.json
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
- [x] Stage 6 — Multi-retailer scraping (Walmart, Amazon, eBay)
- [x] Stage 7 — Deal scoring (0–100, A–D grades)
- [x] Stage 8 — PostgreSQL migration
- [x] Stage 9 — React frontend (Vite + Tailwind + Recharts)
- [x] Stage 10 — Deployment (Render + Vercel)
- [ ] Stage 11 — Tests (pytest + pytest-asyncio)
- [ ] Stage 12 — README screenshots + demo GIF

---

## License

MIT