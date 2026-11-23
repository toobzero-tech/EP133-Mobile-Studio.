import unittest
from import_feeds import parse_feed, parse_date

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><item>
<title>Фотоаппарат</title><link>https://shop.ru/camera</link>
<description>Отличное состояние, цена 12 500 руб.</description>
<pubDate>Mon, 23 Nov 2026 10:00:00 +0000</pubDate>
</item></channel></rss>"""

ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><entry>
<title>Объектив</title><link href="https://shop.ru/lens"/>
<summary>Комплект</summary><updated>2026-11-23T10:00:00Z</updated>
<price>8900</price>
</entry></feed>"""

class FeedImportTests(unittest.TestCase):
    def test_rss_entry_and_ruble_price(self):
        rows = parse_feed(RSS, "partner", "Москва")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Фотоаппарат")
        self.assertEqual(rows[0]["price"], "12500")
        self.assertEqual(rows[0]["location"], "Москва")
        self.assertTrue(rows[0]["published_at"])

    def test_atom_entry_and_explicit_price(self):
        rows = parse_feed(ATOM, "partner")
        self.assertEqual(rows[0]["title"], "Объектив")
        self.assertEqual(rows[0]["url"], "https://shop.ru/lens")
        self.assertEqual(rows[0]["price"], "8900")

    def test_bad_date_is_empty(self):
        self.assertEqual(parse_date("not-a-date"), "")

if __name__ == "__main__":
    unittest.main()
