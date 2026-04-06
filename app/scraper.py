# ============================================================
# scraper.py — GPU prices from:
#   Newegg        — scraping (requests + BeautifulSoup) USD
#   Walmart       — ScraperAPI + __NEXT_DATA__ JSON        USD
#   Amazon        — ScraperAPI + BeautifulSoup             USD
#   Kleinanzeigen — ScraperAPI + BeautifulSoup             EUR
#   eBay          — official Browse API (OAuth2)           USD
#   Best Buy      — stub, needs business email             USD
# ============================================================

import re
import json
import base64
import requests
from bs4 import BeautifulSoup

from app.config import (
    BESTBUY_API_KEY, EBAY_CLIENT_ID,
    EBAY_CLIENT_SECRET, SCRAPERAPI_KEY
)

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
    "graphics card", "video card", "gpu", "grafikkarte",   # German term
]

MIN_PRICE_USD = 150.0
MAX_PRICE_USD = 5000.0
MIN_PRICE_EUR = 140.0
MAX_PRICE_EUR = 4800.0


def is_valid_gpu(name: str, price: float, currency: str = "USD") -> bool:
    name_lower = name.lower()
    if any(kw in name_lower for kw in BLOCKLIST_KEYWORDS):
        return False
    if not any(term in name_lower for term in GPU_ALLOWLIST):
        return False
    min_p = MIN_PRICE_EUR if currency == "EUR" else MIN_PRICE_USD
    max_p = MAX_PRICE_EUR if currency == "EUR" else MAX_PRICE_USD
    return min_p <= price <= max_p


def parse_price(raw: str) -> float | None:
    match = re.search(r"[\d,]+\.?\d*", raw.replace(",", ""))
    return float(match.group()) if match else None


def _scraperapi_get(url: str, extra_params: dict = None) -> requests.Response:
    """Route any URL through ScraperAPI."""
    payload = {"api_key": SCRAPERAPI_KEY, "url": url}
    if extra_params:
        payload.update(extra_params)
    return requests.get("https://api.scraperapi.com/", params=payload, timeout=60)


# ── Newegg ────────────────────────────────────────────────────────────────────

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
            "name": name, "price": parsed, "currency": "USD",
            "link": a_tag["href"], "query": query, "retailer": "newegg",
        })

    print(f"[newegg] '{query}' → {len(results)} listings")
    return results


# ── Walmart ───────────────────────────────────────────────────────────────────

def scrape_walmart(query: str) -> list[dict]:
    if not SCRAPERAPI_KEY:
        print("[walmart] No SCRAPERAPI_KEY — skipping")
        return []

    url = f"https://www.walmart.com/search?q={query.replace(' ', '+')}&cat_id=3944"

    try:
        r = _scraperapi_get(url, {"country_code": "us"})
        r.raise_for_status()
    except Exception as e:
        print(f"[walmart] Request failed for '{query}': {e}")
        return []

    if "Robot or human" in r.text:
        print(f"[walmart] Still blocked for '{query}'")
        return []

    soup   = BeautifulSoup(r.text, "html.parser")
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script:
        print(f"[walmart] __NEXT_DATA__ not found for '{query}'")
        return []

    try:
        data      = json.loads(script.get_text())
        stacks    = (
            data.get("props", {})
                .get("pageProps", {})
                .get("initialData", {})
                .get("searchResult", {})
                .get("itemStacks", [])
        )
        # flatten all stacks and filter to real products only
        raw_items = []
        for stack in stacks:
            for item in stack.get("items", []):
                if item.get("__typename") == "Product":
                    raw_items.append(item)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[walmart] JSON parse error for '{query}': {e}")
        return []

    results = []
    for item in raw_items:
        name  = item.get("name", "")
        price = item.get("price")
        pid   = item.get("usItemId", "")
        link  = f"https://www.walmart.com/ip/{pid}" if pid else ""

        if not name or price is None:
            continue
        try:
            price_f = float(price)
        except (ValueError, TypeError):
            continue
        if not is_valid_gpu(name, price_f):
            continue

        results.append({
            "name": name, "price": price_f, "currency": "USD",
            "link": link, "query": query, "retailer": "walmart",
        })

    print(f"[walmart] '{query}' → {len(results)} listings")
    return results


# ── Amazon ────────────────────────────────────────────────────────────────────

def scrape_amazon(query: str) -> list[dict]:
    if not SCRAPERAPI_KEY:
        print("[amazon] No SCRAPERAPI_KEY — skipping")
        return []

    url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}&i=electronics&rh=n%3A284822"

    try:
        r = _scraperapi_get(url, {"render": "true", "country_code": "us"})
        r.raise_for_status()
    except Exception as e:
        print(f"[amazon] Request failed for '{query}': {e}")
        return []

    soup  = BeautifulSoup(r.text, "html.parser")
    items = soup.find_all("div", {"data-component-type": "s-search-result"})

    if not items:
        print(f"[amazon] No results found for '{query}'")
        return []

    results = []
    for item in items:
        title_tag = item.find("h2")
        if not title_tag:
            continue
        name = title_tag.get_text(strip=True)

        whole = item.find("span", class_="a-price-whole")
        frac  = item.find("span", class_="a-price-fraction")
        if not whole:
            continue
        try:
            price_str = whole.get_text(strip=True).replace(",", "").rstrip(".")
            if frac:
                price_str += "." + frac.get_text(strip=True)
            price_f = float(price_str)
        except (ValueError, AttributeError):
            continue

        a_tag = item.find("a", class_="a-link-normal", href=True)
        link  = "https://www.amazon.com" + a_tag["href"] if a_tag else ""

        if not is_valid_gpu(name, price_f):
            continue

        results.append({
            "name": name, "price": price_f, "currency": "USD",
            "link": link, "query": query, "retailer": "amazon",
        })

    print(f"[amazon] '{query}' → {len(results)} listings")
    return results


# ── Kleinanzeigen (ScraperAPI + German residential proxy) ─────────────────────
# Germany's largest classifieds platform — used/private GPU listings in EUR.

def scrape_kleinanzeigen(query: str) -> list[dict]:
    if not SCRAPERAPI_KEY:
        print("[kleinanzeigen] No SCRAPERAPI_KEY — skipping")
        return []

    # Translate common English GPU terms to German for better results
    de_query = (
        query.replace("graphics card", "grafikkarte")
             .replace("video card", "grafikkarte")
    )
    url = f"https://www.kleinanzeigen.de/s-grafikkarten/{de_query}/k0"

    try:
        r = _scraperapi_get(url, {"country_code": "de", "render": "false"})
        r.raise_for_status()
    except Exception as e:
        print(f"[kleinanzeigen] Request failed for '{query}': {e}")
        return []

    if "captcha" in r.text.lower() or "robot" in r.text.lower():
        print(f"[kleinanzeigen] Blocked for '{query}'")
        return []

    soup  = BeautifulSoup(r.text, "html.parser")
    # Each listing is an <article class="aditem">
    items = soup.find_all("article", class_="aditem")

    if not items:
        print(f"[kleinanzeigen] No listings found for '{query}' — structure may have changed")
        return []

    results = []
    for item in items:
        title_tag = item.find("a", class_="ellipsis")
        if not title_tag:
            continue
        name = title_tag.get_text(strip=True)

        price_tag = item.find("p", class_=lambda c: c and "price" in c)
        if not price_tag:
            continue
        raw_price = price_tag.get_text(strip=True)

        if "verschenken" in raw_price.lower():
            continue

        # Parse European price format (e.g. "1.234,56 €")
        clean = raw_price.replace(".", "").replace(",", ".").replace("€", "").strip()
        parsed = parse_price(clean)
        if parsed is None:
            continue

        href = title_tag.get("href", "")
        link = f"https://www.kleinanzeigen.de{href}" if href.startswith("/") else href

        if not is_valid_gpu(name, parsed, currency="EUR"):
            continue

        results.append({
            "name": name, "price": parsed, "currency": "EUR",
            "link": link, "query": query, "retailer": "kleinanzeigen",
        })

    print(f"[kleinanzeigen] '{query}' → {len(results)} listings")
    return results


# ── Best Buy (stub) ───────────────────────────────────────────────────────────

def scrape_bestbuy(query: str) -> list[dict]:
    if not BESTBUY_API_KEY:
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
            "name": name, "price": float(price), "currency": "USD",
            "link": link, "query": query, "retailer": "bestbuy",
        })

    print(f"[bestbuy] '{query}' → {len(results)} listings")
    return results


# ── eBay ──────────────────────────────────────────────────────────────────────

_ebay_token: dict = {"value": None}


def _get_ebay_token() -> str | None:
    if _ebay_token["value"]:
        return _ebay_token["value"]
    if not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
        print("[ebay] No credentials — skipping")
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
        name     = item.get("title", "")
        price    = item.get("price", {}).get("value")
        currency = item.get("price", {}).get("currency", "USD")
        link     = item.get("itemWebUrl", "")
        if not name or price is None:
            continue
        try:
            price_f = float(price)
        except ValueError:
            continue
        if not is_valid_gpu(name, price_f):
            continue
        results.append({
            "name": name, "price": price_f, "currency": currency,
            "link": link, "query": query, "retailer": "ebay",
        })

    print(f"[ebay] '{query}' → {len(results)} listings")
    return results


# ── Combined ──────────────────────────────────────────────────────────────────

def scrape_gpu(query: str) -> list[dict]:
    results = []
    results.extend(scrape_newegg(query))
    results.extend(scrape_walmart(query))
    results.extend(scrape_amazon(query))
    results.extend(scrape_kleinanzeigen(query))
    results.extend(scrape_bestbuy(query))
    results.extend(scrape_ebay(query))
    return results


def scrape_all(queries: list[str]) -> list[dict]:
    all_results = []
    for query in queries:
        all_results.extend(scrape_gpu(query))
    print(f"[scraper] Total: {len(all_results)} listings across all retailers")
    return all_results