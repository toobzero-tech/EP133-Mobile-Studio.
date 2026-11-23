import unittest
from datetime import datetime, timezone
from market_estimator import estimate


class MarketEstimatorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
        self.listing = [{"id": "lot-1", "brand": "Canon", "model": "EOS 80D", "condition": "Б/У"}]
        self.sales = [
            {"brand": "Canon", "model": "EOS 80D", "condition": "used", "status": "sold",
             "sold_price": p, "sold_at": "2026-11-10T10:00:00Z", "country": "RU", "currency": "RUB",
             "url": "https://example.ru/" + str(p)}
            for p in (30000, 32000, 34000, 36000, 38000)
        ]

    def test_exact_completed_sales_use_median(self):
        result = estimate(self.listing, self.sales, self.now)[0]
        self.assertEqual(result["market_estimate"], 34000)
        self.assertEqual(result["comparable_count"], 5)
        self.assertGreaterEqual(result["confidence"], 65)

    def test_active_listings_are_not_sales(self):
        active = [dict(x, status="active") for x in self.sales]
        result = estimate(self.listing, active, self.now)[0]
        self.assertIsNone(result["market_estimate"])
        self.assertEqual(result["comparable_count"], 0)

    def test_model_and_condition_must_match_exactly(self):
        wrong = [dict(x, model="EOS 90D") for x in self.sales]
        result = estimate(self.listing, wrong, self.now)[0]
        self.assertIsNone(result["market_estimate"])
        wrong_condition = [dict(x, condition="new") for x in self.sales]
        result = estimate(self.listing, wrong_condition, self.now)[0]
        self.assertIsNone(result["market_estimate"])

    def test_foreign_currency_and_old_sales_are_excluded(self):
        bad = [dict(x, currency="EUR") for x in self.sales]
        bad += [dict(x, sold_at="2024-01-01T00:00:00Z") for x in self.sales]
        result = estimate(self.listing, bad, self.now)[0]
        self.assertIsNone(result["market_estimate"])

    def test_duplicate_sale_records_do_not_inflate_comparable_count(self):
        duplicated = self.sales + [dict(self.sales[0]), dict(self.sales[1])]
        result = estimate(self.listing, duplicated, self.now)[0]
        self.assertEqual(result["comparable_count"], 5)

    def test_missing_country_or_currency_is_not_assumed_russian(self):
        incomplete = [dict(x, country=None, currency=None) for x in self.sales]
        result = estimate(self.listing, incomplete, self.now)[0]
        self.assertIsNone(result["market_estimate"])

    def test_single_comparable_has_low_confidence(self):
        result = estimate(self.listing, self.sales[:1], self.now)[0]
        self.assertEqual(result["market_estimate"], 30000)
        self.assertEqual(result["confidence"], 25)


if __name__ == "__main__":
    unittest.main()
