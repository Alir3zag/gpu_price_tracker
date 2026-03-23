# ============================================================
# scraper.py — fetches & parses Newegg search results
# ============================================================

import requests
import re
from bs4 import BeautifulSoup

HEADERS = {
    # pretend to be a real browser — Newegg blocks plain requests without a User-Agent
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def parse_price(raw: str) -> float | None:
    """Strip '$', ',' and whitespace from a price string and return a float.
    Returns None if no valid number is found."""
    match = re.search(r"[\d,]+\.?\d*", raw.replace(",", ""))
    return float(match.group()) if match else None


def scrape_gpu(query: str) -> list[dict]:
    """Search Newegg for `query` and return a list of {name, price, link} dicts."""
    url = f"https://www.newegg.com/p/pl?d={query}&N=4131"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()                         # raise if 4xx / 5xx response
    except requests.RequestException as e:
        print(f"[scraper] Request failed for '{query}': {e}")
        return [dict()]

    doc   = BeautifulSoup(response.text, "html.parser")
    items = doc.find_all("div", class_="item-container")

    results = []
    for item in items:
        a_tag = item.find("a", class_="item-title")         # product name + link
        price = item.find("li", class_="price-current")     # price cell

        if not a_tag or not price:                          # skip ads with missing fields
            continue

        raw_price = price.get_text(strip=True)
        parsed    = parse_price(raw_price)

        if parsed is None:
            continue

        results.append({
            "name"  : a_tag.get_text(strip=True),           # get_text handles nested <span> tags
            "price" : parsed,                               # float, e.g. 1199.99
            "link"  : a_tag["href"],                        # full product URL
            "query" : query,                                # which search produced this result
        })

    print(f"[scraper] '{query}' → {len(results)} items found")
    return results


def scrape_all(queries: list[str]) -> list[dict]:
    """Run scrape_gpu for every query in the list and combine results."""
    all_results = []
    for query in queries:
        all_results.extend(scrape_gpu(query))
    return all_results
