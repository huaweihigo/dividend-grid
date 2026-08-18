"""Build a conservative annual cash-dividend snapshot from AKShare detail records."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from market_utils import security_id, valid_positive_number

ROOT = Path(__file__).resolve().parents[1]
STOCKS_PATH = ROOT / "data" / "stocks.json"
DIVIDENDS_PATH = ROOT / "data" / "dividends.json"
SHANGHAI = ZoneInfo("Asia/Shanghai")


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def annual_cash_dividends(frame) -> dict[str, float]:
    """Sum implemented cash dividends by report year; Eastmoney values are per 10 shares."""
    totals: dict[str, float] = defaultdict(float)
    for _, row in frame.iterrows():
        progress = str(row.get("方案进度", ""))
        report = str(row.get("报告期", ""))
        cash_per_ten = row.get("现金分红-现金分红比例")
        if "实施" not in progress or len(report) < 4 or not valid_positive_number(cash_per_ten):
            continue
        totals[report[:4]] += float(cash_per_ten) / 10
    return {year: round(value, 4) for year, value in totals.items() if value > 0}


def fetch_dividend(stock: dict) -> dict | None:
    try:
        import akshare as ak  # type: ignore
        totals = annual_cash_dividends(ak.stock_fhps_detail_em(symbol=stock["code"]))
        if not totals:
            return None
        year = max(totals)
        return {"annual_dividend": totals[year], "year": year, "source": "AKShare / 东方财富", "updated_at": datetime.now(SHANGHAI).isoformat(timespec="seconds")}
    except Exception as exc:
        print(f"Dividend fetch failed for {security_id(stock)}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


def main() -> int:
    stocks = load_json(STOCKS_PATH, [])
    previous = load_json(DIVIDENDS_PATH, {"stocks": {}})
    fresh, failures = {}, []
    for stock in stocks:
        record = fetch_dividend(stock)
        if record:
            fresh[security_id(stock)] = record
        else:
            failures.append(security_id(stock))
    merged = dict(previous.get("stocks", {}))
    merged.update(fresh)  # failed requests never erase a prior verified dividend
    status = "normal" if len(fresh) == len(stocks) else "partial" if fresh else "failed"
    result = {"schema_version": 1, "status": status, "updated_at": datetime.now(SHANGHAI).isoformat(timespec="seconds"), "source": "AKShare / 东方财富", "message": f"自动更新 {len(fresh)}/{len(stocks)} 只股票的已实施分红；失败项保留旧值。", "stocks": merged, "failures": failures}
    # Avoid a daily commit merely because the script checked the same dividend records again.
    comparable = lambda value: {"status": value.get("status"), "stocks": value.get("stocks", {})}
    if comparable(result) != comparable(previous):
        DIVIDENDS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(result["message"])
    else:
        print("No effective dividend-data change; dividends.json was left untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
