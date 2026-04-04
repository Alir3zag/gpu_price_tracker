# ============================================================
# scraper.py — GPU prices from:
#   Newegg   — scraping (requests + BeautifulSoup)
#   Walmart  — scraping (curl_cffi TLS impersonation + __NEXT_DATA__ JSON)
#   eBay     — official Browse API (OAuth2 client credentials)
#   Best Buy — stub ready, needs business email for API key
# ============================================================

import re
import json
import base64
import requests
from bs4 import BeautifulSoup

try:
    import curl_cffi.requests as curl_requests
    CURL_AVAILABLE = True
except ImportError:
    CURL_AVAILABLE = False
    print("[walmart] curl_cffi not installed — run: pip install curl_cffi")

from app.config import BESTBUY_API_KEY, EBAY_CLIENT_ID, EBAY_CLIENT_SECRET

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Filtering ─────────────────────────────────────────────────────────────────

BLOCKLIST_KEYWORDS = [
    "desktop", "laptop", "notebook", "gaming pc", "computer",
    "windows 11", "windows 10", "ryzen", "core i9", "core i7", "core i5",
    "processor", "motherboard", "ram", "ddr5", "ddr4", "nvme", "ssd", "hdd",
    "monitor", "keyboard", "mouse", "headset", "chair", "case",
]

GPU_ALLOWLIST = [
    "geforce", "radeon", "rtx", "gtx", "rx ", "arc ",
    "graphics card", "video card", "gpu",
]

MIN_PRICE = 150.0
MAX_PRICE = 5000.0


def is_valid_gpu(name: str, price: float) -> bool:
    name_lower = name.lower()
    if any(kw in name_lower for kw in BLOCKLIST_KEYWORDS):
        return False
    if not any(term in name_lower for term in GPU_ALLOWLIST):
        return False
    return MIN_PRICE <= price <= MAX_PRICE


def parse_price(raw: str) -> float | None:
    match = re.search(r"[\d,]+\.?\d*", raw.replace(",", ""))
    return float(match.group()) if match else None


# ── Newegg (scraping) ─────────────────────────────────────────────────────────

def scrape_newegg(query: str) -> list[dict]:
    url = f"https://www.newegg.com/p/pl?d={query}&N=4131"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[newegg] Request failed for '{query}': {e}")
        return []

    doc   = BeautifulSoup(r.text, "html.parser")
    items = doc.find_all("div", class_="item-container")
    results = []

    for item in items:
        a_tag = item.find("a", class_="item-title")
        price = item.find("li", class_="price-current")
        if not a_tag or not price:
            continue
        name   = a_tag.get_text(strip=True)
        parsed = parse_price(price.get_text(strip=True))
        if parsed is None or not is_valid_gpu(name, parsed):
            continue
        results.append({
            "name": name, "price": parsed,
            "link": a_tag["href"], "query": query, "retailer": "newegg",
        })

    print(f"[newegg] '{query}' → {len(results)} listings")
    return results


# ── Walmart (curl_cffi TLS impersonation + __NEXT_DATA__ JSON) ────────────────
# Walmart embeds all search result data in a <script id="__NEXT_DATA__"> JSON
# blob — no fragile CSS selectors needed. curl_cffi impersonates Chrome's TLS
# fingerprint to avoid the "Robot or Human?" CAPTCHA that blocks plain requests.

def scrape_walmart(query: str) -> list[dict]:
    if not CURL_AVAILABLE:
        print("[walmart] Skipping — curl_cffi not installed")
        return []

    url = f"https://www.walmart.com/search?q={query.replace(' ', '+')}&cat_id=3944"

    try:
        r = curl_requests.get(url, impersonate="chrome110", timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[walmart] Request failed for '{query}': {e}")
        return []

    if "Robot or human" in r.text:
        print(f"[walmart] CAPTCHA triggered for '{query}' — blocked this run")
        return []

    soup    = BeautifulSoup(r.text, "html.parser")
    script  = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script:
        print(f"[walmart] __NEXT_DATA__ not found for '{query}' — page structure may have changed")
        return []

    try:
        data = json.loads(script.get_text())
        # Path to search results inside Walmart's Next.js data blob
        items = (
            data.get("props", {})
                .get("pageProps", {})
                .get("initialData", {})
                .get("searchResult", {})
                .get("itemStacks", [{}])[0]
                .get("items", [])
        )
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        print(f"[walmart] JSON parse error for '{query}': {e}")
        return []

    results = []
    for item in items:
        name  = item.get("name", "")
        price = item.get("priceInfo", {}).get("currentPrice", {}).get("price")
        link  = "https://www.walmart.com" + item.get("canonicalUrl", "")

        if not name or price is None:
            continue
        try:
            price_f = float(price)
        except (ValueError, TypeError):
            continue
        if not is_valid_gpu(name, price_f):
            continue

        results.append({
            "name": name, "price": price_f,
            "link": link, "query": query, "retailer": "walmart",
        })

    print(f"[walmart] '{query}' → {len(results)} listings")
    return results


# ── Best Buy (official API) — stub, needs business email ─────────────────────
# Sign up at developer.bestbuy.com once you have a non-Gmail address.
# Uncomment the body below and add BESTBUY_API_KEY to .env when ready.

def scrape_bestbuy(query: str) -> list[dict]:
    if not BESTBUY_API_KEY:
        # Silently skip — no spam on every scrape cycle
        return []

    url = (
        f"https://api.bestbuy.com/v1/products"
        f"(search={query}&categoryPath.id=abcat0507002)"
        f"?apiKey={BESTBUY_API_KEY}"
        f"&show=name,salePrice,url,sku"
        f"&pageSize=10&format=json"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[bestbuy] Request failed for '{query}': {e}")
        return []

    results = []
    for p in data.get("products", []):
        name  = p.get("name", "")
        price = p.get("salePrice")
        link  = p.get("url", "")
        if not name or price is None:
            continue
        if not is_valid_gpu(name, float(price)):
            continue
        results.append({
            "name": name, "price": float(price),
            "link": link, "query": query, "retailer": "bestbuy",
        })

    print(f"[bestbuy] '{query}' → {len(results)} listings")
    return results


# ── eBay (official Browse API) ────────────────────────────────────────────────
# Free — sign up at developer.ebay.com, create an app, copy App ID + Secret.
# Add EBAY_CLIENT_ID and EBAY_CLIENT_SECRET to .env.

_ebay_token: dict = {"value": None}


def _get_ebay_token() -> str | None:
    if _ebay_token["value"]:
        return _ebay_token["value"]
    if not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
        print("[ebay] No credentials — skipping. Add EBAY_CLIENT_ID + EBAY_CLIENT_SECRET to .env")
        return None
    credentials = base64.b64encode(
        f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()
    ).decode()
    try:
        r = requests.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data="grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope",
            timeout=10,
        )
        r.raise_for_status()
        token = r.json().get("access_token")
        _ebay_token["value"] = token
        print("[ebay] OAuth token obtained")
        return token
    except Exception as e:
        print(f"[ebay] Auth failed: {e}")
        return None


def scrape_ebay(query: str) -> list[dict]:
    token = _get_ebay_token()
    if not token:
        return []

    try:
        r = requests.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": query,
                "category_ids": "27386",
                "filter": "buyingOptions:{FIXED_PRICE}",
                "limit": "20",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[ebay] Request failed for '{query}': {e}")
        return []

    results = []
    for item in data.get("itemSummaries", []):
        name  = item.get("title", "")
        price = item.get("price", {}).get("value")
        link  = item.get("itemWebUrl", "")
        if not name or price is None:
            continue
        try:
            price_f = float(price)
        except ValueError:
            continue
        if not is_valid_gpu(name, price_f):
            continue
        results.append({
            "name": name, "price": price_f,
            "link": link, "query": query, "retailer": "ebay",
        })

    print(f"[ebay] '{query}' → {len(results)} listings")
    return results


# ── Combined ──────────────────────────────────────────────────────────────────

def scrape_gpu(query: str) -> list[dict]:
    results = []
    results.extend(scrape_newegg(query))
    results.extend(scrape_walmart(query))
    results.extend(scrape_bestbuy(query))   # silently skips if no API key
    results.extend(scrape_ebay(query))
    return results


def scrape_all(queries: list[str]) -> list[dict]:
    all_results = []
    for query in queries:
        all_results.extend(scrape_gpu(query))
    print(f"[scraper] Total: {len(all_results)} listings across all retailers")
    return all_results
