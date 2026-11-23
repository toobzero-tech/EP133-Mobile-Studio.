import unittest
from unittest.mock import patch
from import_golova_market import listing_to_row, import_cities

class GolovaImportTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            "id": "lot-123", "slug": "camera-sony-a7", "title": "Sony A7",
            "brand": "Sony", "model": "A7", "price": 55000, "currency": "RUB",
            "city": "Москва", "type": "sale", "condition": "used",
            "category": {"name": "Фотооборудование"}, "cover": "https://img.example/photo.webp",
            "seller": {"slug": "seller-1", "name": "Seller", "verified": True}
        }

    def test_valid_russian_sale_maps_to_common_schema(self):
        row = listing_to_row(self.item, "Москва")
        self.assertEqual(row["source"], "golova_market")
        self.assertEqual(row["url"], "https://golovamarket.ru/listings/camera-sony-a7")
        self.assertEqual(row["price"], 55000)
        self.assertEqual(row["country"], "RU")
        self.assertEqual(row["brand"], "Sony")
        self.assertEqual(row["model"], "A7")
        self.assertEqual(row["image_urls"], ["https://img.example/photo.webp"])

    def test_rentals_are_excluded(self):
        item = dict(self.item, type="rent")
        self.assertIsNone(listing_to_row(item, "Москва"))

    def test_foreign_city_result_is_excluded(self):
        item = dict(self.item, city="Минск")
        self.assertIsNone(listing_to_row(item, "Москва"))

    def test_wrong_currency_is_excluded(self):
        item = dict(self.item, currency="USD")
        self.assertIsNone(listing_to_row(item, "Москва"))

    def test_price_on_request_is_excluded(self):
        item = dict(self.item, price=None)
        self.assertIsNone(listing_to_row(item, "Москва"))

    def test_zero_price_and_missing_slug_are_excluded(self):
        self.assertIsNone(listing_to_row(dict(self.item, price=0), "Москва"))
        self.assertIsNone(listing_to_row(dict(self.item, slug=""), "Москва"))

    @patch("import_golova_market.fetch_page")
    @patch("import_golova_market.time.sleep")
    def test_city_scan_deduplicates_and_keeps_only_sale(self, sleep, fetch):
        fetch.return_value = {"data": [self.item, self.item, dict(self.item, type="rent")], "last_page": 1}
        rows, stats, requests = import_cities({"cities": ["Москва"]}, max_pages=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(requests, 1)
        self.assertEqual(stats["accepted"], 1)
        self.assertEqual(stats["duplicates"], 1)
        self.assertEqual(stats["rental_or_invalid"], 1)

if __name__ == "__main__":
    unittest.main()
