#!/usr/bin/env python3
"""Import explicitly authorized public JSON feeds with declared field mappings.

This is a feed client, not a crawler. Every feed must be HTTPS, same-host redirects
only, and explicitly confirmed as Russian with an explicit RUB currency field.
"""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from normalize_import import normalize

MAX_BYTES = 2_000_000
TIMEOUT = 15
USER_AGENT = "PRICE-RADAR-JSON-FEED/0.1 (configured public feeds only)"


def get_path(value, path):
    if not path:
        return value
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


def map_payload(payload, config):
    if config.get("country_confirmed") is not True:
        raise ValueError("Для JSON-фида требуется country_confirmed=true после проверки источника")
    mapping = config.get("fields") or {}
    records = get_path(payload, config.get("items_path", "items"))
    if not isinstance(records, list):
        raise ValueError("items_path должен указывать на массив записей")
    rows = []
    for item in records:
        if not isinstance(item, dict):
            continue
        row = {}
        for target, source_path in mapping.items():
            if isinstance(source_path, str) and source_path:
                value = get_path(item, source_path)
                if value is not None:
                    row[target] = value
        # A constant currency is allowed only when the feed owner documents it
        # and the operator explicitly confirms that declaration in the config.
        if not row.get("currency") and config.get("currency_confirmed") is True:
            row["currency"] = config.get("currency_constant", "")
        row["source"] = config.get("source", "partner")
        row["location"] = row.get("location") or config.get("location", "")
        if config.get("country_confirmed") is True:
            row["country"] = "RU"
        rows.append(row)
    return rows


def fetch_json_feed(config):
    url = config.get("url", "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Разрешены только HTTPS URL публичных JSON-фидов")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != parsed.hostname:
            raise ValueError("Запрещён переход JSON-фида на другой домен или HTTP")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("JSON-фид превышает лимит 2 МБ")
    payload = json.loads(raw.decode("utf-8-sig"))
    return map_payload(payload, config)


def main():
    ap = argparse.ArgumentParser(description="Импорт разрешённых публичных JSON-фидов")
    ap.add_argument("config", help="JSON с массивом feeds")
    ap.add_argument("-o", "--output", default="price_radar_json_feed.json")
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
    rows = []
    for feed in config.get("feeds", []):
        if not feed.get("enabled", False):
            continue
        try:
            batch = fetch_json_feed(feed)
            rows.extend(batch)
            print(f'{feed.get("source", "partner")}: получено записей {len(batch)}')
        except (KeyError, ValueError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f'{feed.get("source", "unknown")}: ошибка импорта: {exc}')
        time.sleep(max(0.0, args.delay))
    normalized = [normalize(row) for row in rows]
    unique = {}
    for row in normalized:
        if row["title"] and row["url"] and row["price"] > 0 and row["eligible_for_russia_feed"]:
            unique.setdefault(row["dedupe_key"], row)
    Path(args.output).write_text(json.dumps(list(unique.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Итого: {len(unique)} уникальных RUB-записей сохранено в {args.output}")


if __name__ == "__main__":
    main()
