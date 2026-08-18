"""Small, dependency-free rules shared by the market updater and tests."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def valid_positive_number(value: Any) -> bool:
    """Return True only for a finite numeric value greater than zero."""
    try:
        number = Decimal(str(value))
    except Exception:
        return False
    return number.is_finite() and number > 0


def dividend_yield_percent(annual_dividend: Any, price: Any) -> float | None:
    """Annual dividend / price as percentage points, or None when unknown."""
    if not valid_positive_number(annual_dividend) or not valid_positive_number(price):
        return None
    return float(Decimal(str(annual_dividend)) / Decimal(str(price)) * 100)


def price_for_yield(annual_dividend: Any, yield_percent: Any) -> float | None:
    """Dividend / (percentage / 100), or None when inputs are not usable."""
    if not valid_positive_number(annual_dividend) or not valid_positive_number(yield_percent):
        return None
    return float(Decimal(str(annual_dividend)) / (Decimal(str(yield_percent)) / 100))


def generate_yield_grid(minimum: Any, maximum: Any, step: Any) -> list[float]:
    """Generate inclusive yield percentages without binary floating point drift."""
    start, end, increment = (Decimal(str(v)) for v in (minimum, maximum, step))
    if start <= 0 or end < start or increment <= 0:
        return []
    values: list[float] = []
    current = start
    while current <= end:
        values.append(float(current))
        current += increment
    return values


def rounded_price(value: float | None) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def security_id(stock: dict[str, Any]) -> str:
    return f"{stock['code']}.{stock['exchange']}"


def preserve_valid_market(
    previous: dict[str, Any], fresh_quotes: dict[str, dict[str, Any]], watched_ids: set[str]
) -> dict[str, dict[str, Any]]:
    """Merge valid new quotes only; missing/invalid quotes never erase old values."""
    result = dict(previous.get("stocks", {}))
    for quote_id, quote in fresh_quotes.items():
        if quote_id in watched_ids and valid_positive_number(quote.get("price")):
            result[quote_id] = quote
    return result

