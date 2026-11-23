import unittest
from normalize_import import normalize, clean_url

class NormalizeTests(unittest.TestCase):
    def test_url_removes_tracking_query(self):
        self.assertEqual(clean_url("https://EXAMPLE.com/item/1?utm_source=x"), "https://example.com/item/1")

    def test_russian_condition_and_price(self):
        row = normalize({"name":"Фотоаппарат","price":"12 500","condition":"Б/У","marketplace":"Мешок","url":"https://meshok.net/item/1"})
        self.assertEqual(row["price"], 12500.0)
        self.assertEqual(row["condition"], "used")
        self.assertEqual(row["source"], "meshok")

    def test_russian_retail_source_aliases(self):
        for label, expected in [("Яндекс Маркет", "yandex_market"), ("Ozon", "ozon"),
                                ("Wildberries", "wildberries"), ("DNS", "dns"),
                                ("М.Видео", "mvideo"), ("Ситилинк", "citilink")]:
            row = normalize({"name": "Товар", "price": "1000", "marketplace": label})
            self.assertEqual(row["source"], expected)
            self.assertEqual(row["country"], "RU")
            self.assertEqual(row["currency"], "RUB")
            self.assertTrue(row["eligible_for_russia_feed"])

    def test_non_ruble_source_is_not_feed_eligible(self):
        row = normalize({"name": "Item", "price": "20", "currency": "EUR", "source": "manual"})
        self.assertEqual(row["currency"], "UNSUPPORTED")
        self.assertFalse(row["eligible_for_russia_feed"])

    def test_condition_aliases_include_open_box(self):
        row = normalize({"name": "Товар", "price": "100", "condition": "витринный образец"})
        self.assertEqual(row["condition"], "open_box")

    def test_publication_and_observation_timestamps_are_separate(self):
        row = normalize({"name": "Товар", "price": "100", "published_at": "2026-11-20T10:00:00Z", "observed_at": "2026-11-23T10:00:00Z"})
        self.assertEqual(row["published_at"], "2026-11-20T10:00:00Z")
        self.assertEqual(row["observed_at"], "2026-11-23T10:00:00Z")

    def test_camel_case_timestamps_are_supported(self):
        row = normalize({"name": "Товар", "price": "100", "publishedAt": "2026-11-20T10:00:00Z", "observedAt": "2026-11-23T10:00:00Z"})
        self.assertEqual(row["published_at"], "2026-11-20T10:00:00Z")
        self.assertEqual(row["observed_at"], "2026-11-23T10:00:00Z")

    def test_missing_url_and_id_has_stable_hash(self):
        a = normalize({"name":"Лот","price":"100","location":"Москва"})
        b = normalize({"name":"Лот","price":"100","location":"Москва"})
        self.assertEqual(a["dedupe_key"], b["dedupe_key"])

if __name__ == "__main__":
    unittest.main()
