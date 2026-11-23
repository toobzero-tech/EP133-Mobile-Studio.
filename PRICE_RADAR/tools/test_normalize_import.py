import unittest
from normalize_import import normalize, clean_url

class NormalizeTests(unittest.TestCase):
    def test_url_removes_tracking_query(self):
        self.assertEqual(clean_url("https://EXAMPLE.com/item/1?utm_source=x"), "https://example.com/item/1")

    def test_russian_condition_and_price(self):
        row = normalize({"name":"Фотоаппарат","price":"12 500","condition":"Б/У","marketplace":"Мешок","url":"https://meshok.net/item/1"})
        self.assertEqual(row["price"], 12500.0)
        self.assertEqual(row["condition"], "used")
        self.assertEqual(row["source"], "мешок")

    def test_missing_url_and_id_has_stable_hash(self):
        a = normalize({"name":"Лот","price":"100","location":"Москва"})
        b = normalize({"name":"Лот","price":"100","location":"Москва"})
        self.assertEqual(a["dedupe_key"], b["dedupe_key"])

if __name__ == "__main__":
    unittest.main()
