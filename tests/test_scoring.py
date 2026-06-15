# tests/test_scoring.py
"""
Unit tests for the deal scoring algorithm.
Imported directly — no HTTP needed.
"""
import pytest
from app.scoring import score_drop, grade


# ── grade() ──────────────────────────────────────────────────────────────────

def test_grade_a():
    assert grade(80) == "A"
    assert grade(100) == "A"
    assert grade(95.5) == "A"


def test_grade_b():
    assert grade(60) == "B"
    assert grade(79.9) == "B"


def test_grade_c():
    assert grade(40) == "C"
    assert grade(59.9) == "C"


def test_grade_d():
    assert grade(0) == "D"
    assert grade(39.9) == "D"
    assert grade(39) == "D"


# ── score_drop() ─────────────────────────────────────────────────────────────

def test_score_in_valid_range():
    s = score_drop(
        drop_pct=10.0,
        price_history=[800.0, 750.0, 700.0],
        current_price=700.0,
        all_current=[{"name": "RTX 3080", "price": 700.0}],
        gpu_name="RTX 3080",
    )
    assert 0 <= s <= 100


def test_zero_drop_gives_low_score():
    s = score_drop(
        drop_pct=0.0,
        price_history=[700.0],
        current_price=700.0,
        all_current=[{"name": "RTX 3080", "price": 700.0}],
        gpu_name="RTX 3080",
    )
    assert s < 40  # zero drop should be D grade


def test_large_drop_gives_high_score():
    s = score_drop(
        drop_pct=30.0,
        price_history=[1000.0, 950.0, 700.0],
        current_price=700.0,
        all_current=[{"name": "RTX 3080", "price": 700.0}],
        gpu_name="RTX 3080",
    )
    assert s >= 60  # 30% drop should be at least B


def test_all_time_low_boosts_score():
    """Price at all-time low should score higher than same drop % not at all-time low."""
    history = [1000.0, 900.0, 800.0, 700.0]

    score_at_low = score_drop(
        drop_pct=30.0,
        price_history=history,
        current_price=700.0,  # equals historical low
        all_current=[{"name": "GPU", "price": 700.0}],
        gpu_name="GPU",
    )
    score_above_low = score_drop(
        drop_pct=10.0,
        price_history=history,
        current_price=900.0,  # above historical low
        all_current=[{"name": "GPU", "price": 900.0}],
        gpu_name="GPU",
    )
    assert score_at_low > score_above_low


def test_cheapest_across_retailers_boosts_score():
    """Being cheapest in a pool should give higher score than being the most expensive."""
    all_current = [
        {"name": "RTX 3080", "price": 500.0},
        {"name": "RTX 3080", "price": 700.0},
        {"name": "RTX 3080", "price": 900.0},
    ]
    score_cheapest = score_drop(
        drop_pct=10.0,
        price_history=[700.0],
        current_price=500.0,
        all_current=all_current,
        gpu_name="RTX 3080",
    )
    score_priciest = score_drop(
        drop_pct=10.0,
        price_history=[1000.0],
        current_price=900.0,
        all_current=all_current,
        gpu_name="RTX 3080",
    )
    assert score_cheapest > score_priciest


def test_empty_history_does_not_crash():
    s = score_drop(
        drop_pct=15.0,
        price_history=[],
        current_price=500.0,
        all_current=[{"name": "RTX 3080", "price": 500.0}],
        gpu_name="RTX 3080",
    )
    assert 0 <= s <= 100


def test_single_item_all_current():
    s = score_drop(
        drop_pct=20.0,
        price_history=[800.0, 700.0],
        current_price=700.0,
        all_current=[{"name": "RTX 3080", "price": 700.0}],
        gpu_name="RTX 3080",
    )
    assert 0 <= s <= 100
