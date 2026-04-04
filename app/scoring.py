# ============================================================
# scoring.py — deal quality scorer for price drop alerts
#
# Score is 0–100 based on three weighted factors:
#   40% — drop size (how big is the percentage drop)
#   35% — historical rarity (how often has this GPU dropped this much)
#   25% — cross-retailer position (is this the cheapest place right now)
#
# Pure functions, no DB access — all data passed in by the caller.
# ============================================================

def score_drop(
    drop_pct:       float,          # e.g. 18.5  (percent)
    price_history:  list[float],    # all historical prices for this GPU, oldest first
    current_price:  float,          # the new (dropped) price
    all_current:    list[dict],     # full current scrape results (all retailers)
    gpu_name:       str,            # used to find cross-retailer matches
) -> float:
    """Return a deal quality score from 0 to 100.

    Factors and weights:
        drop_score      (0–100) × 0.40
        rarity_score    (0–100) × 0.35
        position_score  (0–100) × 0.25
    """
    drop_score     = _score_drop_size(drop_pct)
    rarity_score   = _score_rarity(drop_pct, price_history, current_price)
    position_score = _score_cross_retailer(current_price, gpu_name, all_current)

    total = (
        drop_score     * 0.40 +
        rarity_score   * 0.35 +
        position_score * 0.25
    )
    return round(min(max(total, 0.0), 100.0), 1)


def grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 80: return "A"
    if score >= 60: return "B"
    if score >= 40: return "C"
    return "D"


# ── Factor 1 — drop size (40%) ────────────────────────────────────────────────

def _score_drop_size(drop_pct: float) -> float:
    """Map drop percentage to 0–100.

    Scale:
        5%  →  0   (just at threshold, not impressive)
        10% → 33
        20% → 67
        30% → 100  (capped — anything above 30% is exceptional)
    """
    capped = min(drop_pct, 30.0)
    return (capped / 30.0) * 100.0


# ── Factor 2 — historical rarity (35%) ───────────────────────────────────────

def _score_rarity(
    drop_pct:      float,
    price_history: list[float],
    current_price: float,
) -> float:
    """Score how rare this drop is based on historical prices.

    Logic:
    - If no history (new product), return 50 — neutral, not penalised
    - Find the lowest historical price ever seen for this GPU
    - If current price beats the historical low → score 100
    - If current price is at the historical low → score 80
    - Otherwise, score based on how far current is from the all-time low
    """
    if len(price_history) < 2:
        return 50.0     # not enough history to judge — neutral score

    historical_low = min(price_history)

    if current_price < historical_low:
        return 100.0    # new all-time low — exceptional

    if current_price == historical_low:
        return 80.0

    # How close is the current price to the historical low?
    # Distance from low as a fraction of the price range
    historical_high = max(price_history)
    price_range     = historical_high - historical_low

    if price_range == 0:
        return 50.0     # price has never moved — neutral

    distance_from_low = current_price - historical_low
    closeness         = 1.0 - (distance_from_low / price_range)   # 1.0 = at low, 0.0 = at high
    return round(closeness * 80.0, 1)   # max 80 — can't hit 100 unless it's a new low


# ── Factor 3 — cross-retailer position (25%) ─────────────────────────────────

def _score_cross_retailer(
    current_price: float,
    gpu_name:      str,
    all_current:   list[dict],
) -> float:
    """Score how this price compares to the same GPU at other retailers.

    Logic:
    - Find all listings in the current scrape that match this GPU name
    - If only one retailer has it → neutral (50)
    - If this is the cheapest → 100
    - If this is the most expensive → 0
    - Otherwise → linear interpolation between cheapest and most expensive
    """
    name_lower = gpu_name.lower()

    # Fuzzy match — same GPU can have slightly different names across retailers
    # Match on the first 40 chars to catch minor suffix differences
    match_key = name_lower[:40]
    matching_prices = [
        item["price"]
        for item in all_current
        if item.get("name", "").lower()[:40] == match_key
        and item.get("price") is not None
    ]

    if len(matching_prices) <= 1:
        return 50.0     # only one source — can't compare

    lowest  = min(matching_prices)
    highest = max(matching_prices)

    if highest == lowest:
        return 50.0     # all retailers same price

    if current_price <= lowest:
        return 100.0

    if current_price >= highest:
        return 0.0

    position = (highest - current_price) / (highest - lowest)  # 1.0 = cheapest
    return round(position * 100.0, 1)
