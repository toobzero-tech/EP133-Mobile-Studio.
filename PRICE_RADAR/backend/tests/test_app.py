import json
import os
import unittest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

import app
import gemini_analysis


class PriceRadarApiTests(unittest.TestCase):
    def test_gemini_image_url_allowlist_rejects_external_hosts(self):
        self.assertTrue(gemini_analysis._safe_image_url("https://10.img.avito.st/photo.jpg"))
        self.assertFalse(gemini_analysis._safe_image_url("https://example.com/photo.jpg"))
        self.assertFalse(gemini_analysis._safe_image_url("http://10.img.avito.st/photo.jpg"))

    def test_gemini_analysis_requires_server_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                gemini_analysis.analyze_listing({"title": "Camera"})

    def test_gemini_uses_stateless_interactions_api_and_suppresses_unverified_price(self):
        payload = {"output": [{"type": "text", "text": json.dumps({"identification": "Фотоаппарат", "search_query": "Зенит TTL", "market_value_min": 1000, "market_value_max": 5000})}]}
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("gemini_analysis.urllib.request.urlopen", return_value=response) as mocked:
                result = gemini_analysis.analyze_listing({"title": "Camera", "images": []})
        self.assertEqual(result["identification"], "Фотоаппарат")
        self.assertEqual(result["search_query"], "Зенит TTL")
        self.assertIsNone(result["market_value_min"])
        self.assertIsNone(result["market_value_max"])
        self.assertEqual(result["images_analyzed"], 0)
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, gemini_analysis.INTERACTIONS_URL)
        body = json.loads(request.data.decode())
        self.assertFalse(body["store"])
        self.assertEqual(body["model"], "gemini-3.8-flash")
        self.assertEqual(body["input"][0]["type"], "text")

    def test_interactions_output_text_extracts_multiple_text_parts(self):
        payload = {"output": [{"type": "text", "text": "first"}, {"content": [{"type": "text", "text": "second"}]}]}
        self.assertEqual(gemini_analysis._extract_output_text(payload), "first\\nsecond")

    def test_comparison_rejects_ids_not_in_avito_candidates(self):
        payload = {"output": [{"type": "text", "text": json.dumps({"comparable_ids": ["123", "attacker-id", "456"], "confidence": 150, "reason": "same model"})}]}
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        candidates = [{"id": "123", "title": "A", "price": 100}, {"id": "456", "title": "B", "price": 200}]
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("gemini_analysis.urllib.request.urlopen", return_value=response):
                result = gemini_analysis.compare_listing({"title": "A"}, {"identification": "A"}, candidates)
        self.assertEqual(result["comparable_ids"], ["123", "456"])
        self.assertEqual(result["confidence"], 100)

    def test_only_https_avito_urls_are_allowed(self):
        self.assertTrue(app._allowed_avito_url("https://www.avito.ru/moskva/telefony/item_123"))
        self.assertTrue(app._allowed_avito_url("https://avito.ru/item_123"))
        self.assertFalse(app._allowed_avito_url("http://www.avito.ru/item_123"))
        self.assertFalse(app._allowed_avito_url("https://example.com/item_123"))

    def test_listing_requires_explicit_rub_and_valid_avito_link(self):
        base = {"id": 1, "url": "https://www.avito.ru/item_1", "title": "Camera", "price": 1000, "currency": "RUB"}
        self.assertIsNotNone(app._normalise_listing(base))
        no_currency = dict(base)
        no_currency.pop("currency")
        self.assertIsNone(app._normalise_listing(no_currency))
        foreign_link = dict(base, url="https://example.com/item_1")
        self.assertIsNone(app._normalise_listing(foreign_link))

    def test_real_search_category_and_publication_fields_are_normalised(self):
        item = {
            "id": 123,
            "url": "https://www.avito.ru/moskva/item_123",
            "title": "Film camera",
            "price": 2500,
            "currency": "RUB",
            "published": "2026-11-28T08:00:00.000Z",
            "category": {"id": 4, "name": "Фототехника", "slug": "fototehnika"},
            "params": "Б/у, исправен",
            "images": ["https://img.avito.st/photo.jpg"],
            "seller": {"name": "Продавец"},
        }
        result = app._normalise_listing(item)
        self.assertEqual(result["category"], "Фототехника")
        self.assertEqual(result["published_at"], item["published"])
        self.assertEqual(result["condition"], "Б/у, исправен")
        self.assertEqual(result["images"], item["images"])

    def test_index_route_serves_existing_frontend(self):
        response = app.index()
        self.assertTrue(str(response.path).endswith("PRICE_RADAR/index.html"))
        self.assertTrue(__import__("pathlib").Path(response.path).is_file())

    def test_missing_key_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                app.call_apish({"q": "camera"})
        self.assertEqual(ctx.exception.status_code, 503)

    def test_daily_credit_limit_blocks_extra_calls(self):
        from datetime import datetime, timezone
        with patch.dict(os.environ, {"APISH_API_KEY": "test-key"}):
            with patch.object(app, "API_DAILY_LIMIT", 1), patch.object(app, "API_MIN_INTERVAL", 0):
                app._usage_day = datetime.now(timezone.utc).date().isoformat()
                app._usage_count = 0
                app._last_call = 0.0
                with patch("app.urllib.request.urlopen", side_effect=Exception("should not be called")):
                    try:
                        app.call_apish({"q": "camera"})
                    except Exception:
                        pass
                with self.assertRaises(HTTPException) as ctx:
                    app.call_apish({"q": "camera"})
                self.assertEqual(ctx.exception.status_code, 429)

    def test_apish_request_uses_header_and_parses_response(self):
        payload = {"total": 1, "page": 1, "count": 1, "next_page": None, "credits_used": 5, "listings": []}
        response = MagicMock()
        response.__enter__.return_value.status = 200
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        response.__enter__.return_value.geturl.return_value = app.API_URL + "?q=camera"
        with patch.dict(os.environ, {"APISH_API_KEY": "test-key"}):
            with patch("app.urllib.request.urlopen", return_value=response) as mocked:
                result = app.call_apish({"q": "camera"})
        self.assertEqual(result["total"], 1)
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("X-api-key"), "test-key")
        self.assertNotIn("test-key", request.full_url)


if __name__ == "__main__":
    unittest.main()
