"""Refresh A-share closing prices while never replacing good data with bad data.

No token is needed. AKShare is attempted first. If it is unavailable or does not
return a valid quote, the script falls back per security to Eastmoney's public
quote endpoint. All timestamps are Asia/Shanghai.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from market_utils import preserve_valid_market, security_id, valid_positive_number

ROOT = Path(__file__).resolve().parents[1]
STOCKS_PATH = ROOT / "data" / "stocks.json"
MARKET_PATH = ROOT / "data" / "market.json"
SHANGHAI = ZoneInfo("Asia/Shanghai")


def now_shanghai() -> datetime:
    return datetime.now(SHANGHAI)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def normalize_quote(stock: dict[str, Any], price: Any, source: str, as_of: str | None = None) -> dict[str, Any] | None:
    if not valid_positive_number(price):
        return None
    return {
        "code": stock["code"],
        "name": stock["name"],
        "price": round(float(price), 2),
        "as_of": as_of or now_shanghai().date().isoformat(),
        "updated_at": now_shanghai().isoformat(timespec="seconds"),
        "source": source,
    }


def fetch_with_akshare(stocks: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Obtain the all-market snapshot once, then select watched security codes."""
    try:
        import akshare as ak  # type: ignore
        frame = ak.stock_zh_a_spot_em()
    except Exception as exc:
        return {}, [f"AKShare: {type(exc).__name__}: {exc}"]

    code_column = "代码"
    price_column = "最新价"
    if code_column not in frame.columns or price_column not in frame.columns:
        return {}, ["AKShare: 返回字段不符合预期"]
    prices = {str(row[code_column]).zfill(6): row[price_column] for _, row in frame.iterrows()}
    quotes: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for stock in stocks:
        quote = normalize_quote(stock, prices.get(stock["code"]), "AKShare / 东方财富")
        if quote:
            quotes[security_id(stock)] = quote
        else:
            missing.append(f"AKShare: {security_id(stock)} 无有效价格")
    return quotes, missing


def eastmoney_secid(stock: dict[str, Any]) -> str:
    return f"{1 if stock['exchange'] == 'SH' else 0}.{stock['code']}"


def fetch_with_eastmoney(stock: dict[str, Any]) -> dict[str, Any] | None:
    url = "https://push2.eastmoney.com/api/qt/stock/get?secid={}&fields=f43,f57,f58,f124".format(eastmoney_secid(stock))
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 dividend-grid/1.0", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:  # nosec B310 - fixed public HTTPS endpoint
            payload = json.loads(response.read().decode("utf-8"))
        data = payload.get("data") or {}
        # Eastmoney's f43 is price in cents for A shares.
        # f57 must echo the requested code. Do not accept a quote for another security.
        if str(data.get("f57", "")).zfill(6) != stock["code"]:
            return None
        if str(data.get("f58", "")).strip() and not valid_positive_number(data.get("f43")):
            return None
        price = float(data["f43"]) / 100
        timestamp = data.get("f124")
        as_of = datetime.fromtimestamp(int(timestamp), tz=SHANGHAI).date().isoformat() if timestamp else None
        return normalize_quote(stock, price, "东方财富公开行情", as_of)
    except Exception as exc:
        print(f"Eastmoney failed for {security_id(stock)}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


def build_market(stocks: list[dict[str, Any]], previous: dict[str, Any], use_network: bool = True) -> dict[str, Any]:
    watched = {security_id(stock) for stock in stocks}
    fresh_quotes: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    if use_network:
        fresh_quotes, failures = fetch_with_akshare(stocks)
        for stock in stocks:
            quote_id = security_id(stock)
            if quote_id not in fresh_quotes:
                fallback = fetch_with_eastmoney(stock)
                if fallback:
                    fresh_quotes[quote_id] = fallback
                else:
                    failures.append(f"东方财富: {quote_id} 无有效价格")

    merged_stocks = preserve_valid_market(previous, fresh_quotes, watched)
    success_count = len(fresh_quotes)
    attempted_at = now_shanghai().isoformat(timespec="seconds")
    if success_count == len(stocks) and stocks:
        status, message = "normal", "全部关注股票行情已更新。"
    elif success_count:
        status, message = "partial", f"本次更新了 {success_count}/{len(stocks)} 只；缺失项保留上次有效价格。"
    else:
        status = "failed" if previous.get("stocks") else "unavailable"
        message = "本次行情更新失败，已保留上次有效行情；请稍后在 Actions 中重试。"

    sources = sorted({quote["source"] for quote in fresh_quotes.values()})
    return {
        "schema_version": 1,
        "status": status,
        "as_of": now_shanghai().date().isoformat() if success_count else previous.get("as_of"),
        # An unsuccessful request is not a data update. Keep the last successful timestamp.
        "updated_at": attempted_at if success_count else previous.get("updated_at"),
        "attempted_at": attempted_at,
        "source": "；".join(sources) if sources else previous.get("source"),
        "message": message,
        "stocks": merged_stocks,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="更新 dividend-grid 的市场行情")
    parser.add_argument("--dry-run", action="store_true", help="联网抓取但不写入 data/market.json")
    args = parser.parse_args()
    stocks = load_json(STOCKS_PATH, [])
    previous = load_json(MARKET_PATH, {"stocks": {}})
    if not isinstance(stocks, list) or not stocks:
        print("stocks.json 不是非空数组，拒绝更新。", file=sys.stderr)
        return 2
    market = build_market(stocks, previous)
    print(f"{market['status']}: {market['message']}")
    if not args.dry_run:
        MARKET_PATH.write_text(json.dumps(market, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # A failed update is logged but not made fatal: preserving yesterday's valid file is intentional.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
