import unittest
from import_json_feeds import map_payload, get_path

class JsonFeedTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "source": "partner",
            "items_path": "data.offers",
            "country_confirmed": True,
            "currency_confirmed": False,
            "fields": {
                "title": "product.name",
                "url": "links.public",
                "price": "pricing.amount",
                "currency": "pricing.currency",
                "source_id": "id",
                "published_at": "dates.published",
                "condition": "state"
            }
        }
        self.payload = {"data": {"offers": [{
            "id": "lot-1",
            "product": {"name": "Камера"},
            "links": {"public": "https://partner.ru/item/1"},
            "pricing": {"amount": 12500, "currency": "RUB"},
            "dates": {"published": "2026-11-23T10:00:00Z"},
            "state": "Б/У"
        }]}}

    def test_nested_mapping(self):
        rows = map_payload(self.payload, self.config)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Камера")
        self.assertEqual(rows[0]["price"], 12500)
        self.assertEqual(rows[0]["currency"], "RUB")
        self.assertEqual(rows[0]["source_id"], "lot-1")

    def test_constant_currency_requires_explicit_confirmation(self):
        config = dict(self.config)
        config["fields"] = dict(self.config["fields"])
        config["fields"].pop("currency")
        config["currency_constant"] = "RUB"
        rows = map_payload(self.payload, config)
        self.assertNotIn("currency", rows[0])
        config["currency_confirmed"] = True
        rows = map_payload(self.payload, config)
        self.assertEqual(rows[0]["currency"], "RUB")

    def test_country_confirmation_required(self):
        config = dict(self.config)
        config["country_confirmed"] = False
        with self.assertRaises(ValueError):
            map_payload(self.payload, config)

    def test_invalid_items_path_rejected(self):
        config = dict(self.config)
        config["items_path"] = "missing"
        with self.assertRaises(ValueError):
            map_payload(self.payload, config)

    def test_array_index_path(self):
        self.assertEqual(get_path({"items": [{"name": "x"}]}, "items.0.name"), "x")

if __name__ == "__main__":
    unittest.main()
