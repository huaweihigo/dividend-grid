import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from market_utils import dividend_yield_percent, generate_yield_grid, price_for_yield, preserve_valid_market, valid_positive_number
from update_market import build_market


class CalculationTests(unittest.TestCase):
    def test_dividend_yield(self):
        self.assertAlmostEqual(dividend_yield_percent(2.02, 38.20), 5.287958, places=5)

    def test_price_for_yield(self):
        self.assertAlmostEqual(price_for_yield(2.02, 5), 40.40, places=2)

    def test_grid_has_no_float_tail(self):
        grid = generate_yield_grid(4.0, 7.0, 0.1)
        self.assertEqual(len(grid), 31)
        self.assertEqual(grid[0], 4.0)
        self.assertEqual(grid[15], 5.5)
        self.assertEqual(grid[-1], 7.0)

    def test_missing_values_are_not_prices_or_yields(self):
        self.assertIsNone(dividend_yield_percent(None, 38.2))
        self.assertIsNone(dividend_yield_percent(2.02, None))
        self.assertIsNone(price_for_yield(None, 5))
        self.assertFalse(valid_positive_number(0))
        self.assertFalse(valid_positive_number(float("nan")))

    def test_bad_quote_does_not_erase_previous_market(self):
        previous = {"stocks": {"600036.SH": {"price": 38.2}}}
        merged = preserve_valid_market(previous, {"600036.SH": {"price": 0}}, {"600036.SH"})
        self.assertEqual(merged["600036.SH"]["price"], 38.2)

    def test_missing_quote_does_not_erase_previous_market(self):
        previous = {"stocks": {"600036.SH": {"price": 38.2}}}
        merged = preserve_valid_market(previous, {}, {"600036.SH"})
        self.assertEqual(merged["600036.SH"]["price"], 38.2)

    def test_complete_fetch_failure_preserves_market_file_content(self):
        stock = {"code": "600036", "exchange": "SH", "name": "招商银行"}
        previous = {"as_of": "2026-08-17", "source": "此前有效行情", "stocks": {"600036.SH": {"price": 38.2}}}
        market = build_market([stock], previous, use_network=False)
        self.assertIn(market["status"], {"failed", "unavailable"})
        self.assertEqual(market["stocks"]["600036.SH"]["price"], 38.2)


if __name__ == "__main__":
    unittest.main()
