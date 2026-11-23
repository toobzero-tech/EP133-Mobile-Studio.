#!/usr/bin/env python3
"""Fetch configured public RSS/Atom feeds and normalize Russian listings.

Only explicitly configured HTTPS feed URLs are fetched. This is not a web scraper.
"""
import argparse
import json
import re
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

from normalize_import import normalize

USER_AGENT = "PRICE-RADAR-RSS/0.1 (configured public feeds only)"
MAX_BYTES = 2_000_000
TIMEOUT = 15

def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()

def parse_date(value):
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            return ""

def child_text(node, names):
    for child in list(node):
        if local_name(child.tag) in names and child.text:
            return child.text.strip()
    return ""

def entry_link(node):
    for child in list(node):
        if local_name(child.tag) == "link":
            href = child.attrib.get("href", "").strip()
            if href:
                return href
            if child.text:
                return child.text.strip()
    return ""

def parse_feed(xml_bytes, source, location=""):
    root = ET.fromstring(xml_bytes)
    entries = [n for n in root.iter() if local_name(n.tag) in {"item", "entry", "offer"}]
    rows = []
    for item in entries:
        is_offer = local_name(item.tag) == "offer"
        title = child_text(item, {"name", "title"}) if is_offer else child_text(item, {"title"})
        link = child_text(item, {"url"}) if is_offer else entry_link(item)
        description = child_text(item, {"description", "summary", "content", "encoded"})
        published = child_text(item, {"pubdate", "published", "updated", "date"})
        price = ""
        currency = ""
        if is_offer:
            price = child_text(item, {"price"})
            currency = child_text(item, {"currencyid"})
            if item.attrib.get("available", "true").lower() == "false":
                continue
        else:
            for node in item.iter():
                if local_name(node.tag) in {"price", "amount"} and node.text:
                    price = node.text.strip()
                    break
            if not price:
                match = re.search(r"(?<!\d)(\d[\d\s\u00a0]{1,12}(?:[,.]\d{1,2})?)\s*(?:₽|руб\.?|рублей)", description, re.I)
                if match:
                    price = re.sub(r"[\s\u00a0]", "", match.group(1)).replace(",", ".")
        row = {
            "source": source, "title": title, "url": link,
            "description": description, "price": price,
            "currency": currency, "location": location,
            "published_at": parse_date(published),
        }
        if is_offer and item.attrib.get("id"):
            row["source_id"] = item.attrib["id"]
        rows.append(row)
    return rows

def fetch_feed(url, source, location=""):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Разрешены только HTTPS URL публичных фидов")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != parsed.hostname:
            raise ValueError("Запрещён переход фида на другой домен или HTTP")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Фид превышает лимит 2 МБ")
    return parse_feed(data, source, location)

def main():
    ap = argparse.ArgumentParser(description="Импорт публичных RSS/Atom фидов, явно перечисленных в конфиге")
    ap.add_argument("config", help="JSON с массивом feeds")
    ap.add_argument("-o", "--output", default="price_radar_feed.json")
    ap.add_argument("--delay", type=float, default=2.0, help="Пауза между источниками")
    args = ap.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rows = []
    for feed in config.get("feeds", []):
        if not feed.get("enabled", True):
            continue
        try:
            batch = fetch_feed(feed["url"], feed["source"], feed.get("location", ""))
            rows.extend(batch)
            print(f'{feed["source"]}: получено записей {len(batch)}')
        except (KeyError, ValueError, urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
            print(f'{feed.get("source", "unknown")}: ошибка импорта: {exc}')
        time.sleep(max(0.0, args.delay))
    normalized = [normalize(row) for row in rows]
    unique = {}
    for row in normalized:
        if row["title"] and row["url"] and row["price"] > 0 and row["eligible_for_russia_feed"]:
            unique.setdefault(row["dedupe_key"], row)
    Path(args.output).write_text(json.dumps(list(unique.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Итого: {len(unique)} уникальных записей сохранено в {args.output}")

if __name__ == "__main__":
    main()
