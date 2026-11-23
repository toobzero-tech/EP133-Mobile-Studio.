#!/usr/bin/env python3
"""Import sale listings from Golova.Market's documented public read-only API.

Only configured Russian cities are queried. Records are accepted only when the
API returns the exact requested city, type=sale, explicit RUB, positive price,
a title, and a public listing slug. Rentals and price-on-request are excluded.
"""
import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from normalize_import import normalize

API = "https://golovamarket.ru/api/public/listings"
SITE = "https://golovamarket.ru/listings/"
MAX_BYTES = 2_000_000
TIMEOUT = 20
USER_AGENT = "PRICE-RADAR-Golova-API/1.0 (public read-only API; 1.1s request interval)"


def fetch_page(city, page=1, per_page=50):
    query = urllib.parse.urlencode({
        "city": city,
        "per_page": str(min(50, max(1, per_page))),
        "page": str(max(1, page)),
        "sort": "newest",
    })
    request = urllib.request.Request(
        API + "?" + query,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        if response.status != 200:
            raise RuntimeError("Golova API HTTP " + str(response.status))
        final_url = urllib.parse.urlparse(response.geturl())
        if final_url.scheme != "https" or final_url.hostname != "golovamarket.ru":
            raise RuntimeError("Unexpected API redirect host or scheme")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise RuntimeError("Golova API response exceeds 2 MB")
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Unexpected Golova API response: expected paginator with data[]")
    return payload


def city_key(value):
    return " ".join(str(value or "").casefold().replace("ё", "е").split())


def listing_to_row(item, requested_city):
    if not isinstance(item, dict):
        return None
    # Only actual sale listings can be resale candidates. Rentals are not goods.
    if str(item.get("type") or "").strip().lower() != "sale":
        return None
    city = str(item.get("city") or "").strip()
    if city_key(city) != city_key(requested_city):
        return None
    currency = str(item.get("currency") or "").strip().upper()
    if currency not in {"RUB", "RUR", "₽", "РУБ", "РУБ."}:
        return None
    try:
        price = float(str(item.get("price", "")).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None
    slug = str(item.get("slug") or "").strip()
    title = str(item.get("title") or "").strip()
    if not slug or not title or price <= 0:
        return None
    category = item.get("category")
    if isinstance(category, dict):
        category = category.get("name") or category.get("slug") or ""
    seller = item.get("seller") if isinstance(item.get("seller"), dict) else {}
    image_urls = []
    cover = item.get("cover")
    if isinstance(cover, str) and cover.startswith("https://"):
        image_urls.append(cover)
    for image in item.get("images") or []:
        if isinstance(image, dict):
            src = image.get("src") or image.get("url")
            if isinstance(src, str) and src.startswith("https://") and src not in image_urls:
                image_urls.append(src)
    return {
        "source": "golova_market",
        "source_id": str(item.get("id") or slug),
        "url": SITE + urllib.parse.quote(slug, safe="-"),
        "title": title,
        "description": "",
        "category": category,
        "brand": item.get("brand") or "",
        "model": item.get("model") or "",
        "condition": item.get("condition") or "unknown",
        "price": price,
        "currency": "RUB",
        "country": "RU",  # exact city query against the configured RF city list
        "location": city,
        "published_at": "",  # list endpoint does not expose publication date
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "seller_id": seller.get("slug") or seller.get("id") or "",
        "image_urls": image_urls,
        "listing_type": "fixed",
        "raw": {
            "type": item.get("type"),
            "price_unit": item.get("price_unit"),
            "condition_grade": item.get("condition_grade"),
            "grade_label": item.get("grade_label"),
            "seller_name": seller.get("name"),
            "seller_verified": seller.get("verified"),
        },
    }


def import_cities(config, delay=1.1, max_pages=2, per_page=50):
    cities = config.get("cities") or []
    if not isinstance(cities, list) or not cities:
        raise ValueError("В конфиге нужен непустой список российских городов cities")
    unique = {}
    requests = 0
    stats = {"received": 0, "accepted": 0, "rental_or_invalid": 0, "duplicates": 0, "failed_cities": 0}
    for city in cities:
        city = str(city).strip()
        if not city:
            continue
        for page in range(1, max(1, max_pages) + 1):
            try:
                payload = fetch_page(city, page=page, per_page=per_page)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                stats["failed_cities"] += 1
                print(f"Ошибка источника для города {city}, страница {page}: {exc}")
                break
            requests += 1
            items = payload.get("data") or []
            stats["received"] += len(items)
            for item in items:
                row = listing_to_row(item, city)
                if row is None:
                    stats["rental_or_invalid"] += 1
                    continue
                normalized = normalize(row)
                if not normalized["eligible_for_russia_feed"]:
                    stats["rental_or_invalid"] += 1
                    continue
                key = normalized["dedupe_key"]
                if key in unique:
                    stats["duplicates"] += 1
                else:
                    unique[key] = normalized
                    stats["accepted"] += 1
            last_page = int(payload.get("last_page") or 1)
            if page >= min(last_page, max(1, max_pages)):
                break
            time.sleep(max(1.05, delay))
        time.sleep(max(1.05, delay))
    return list(unique.values()), stats, requests


def main():
    parser = argparse.ArgumentParser(description="Импорт продаж Golova.Market по российским городам")
    parser.add_argument("config", help="JSON-конфигурация со списком cities")
    parser.add_argument("-o", "--output", default="golova_market_offers.json")
    parser.add_argument("--delay", type=float, default=1.1, help="Пауза между API-запросами, минимум 1.05 сек")
    parser.add_argument("--max-pages", type=int, default=2, help="Максимум страниц на город")
    parser.add_argument("--per-page", type=int, default=50, help="Записей на страницу, максимум 50")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
    rows, stats, requests = import_cities(
        config, delay=args.delay, max_pages=args.max_pages, per_page=args.per_page
    )
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Источник: Golova.Market public API")
    print("API-запросов:", requests)
    print("Получено записей:", stats["received"])
    print("Продаж в RUB после фильтра:", stats["accepted"])
    print("Исключено (аренда/неполные/не RUB):", stats["rental_or_invalid"])
    print("Дубликатов:", stats["duplicates"])
    print("Городов с ошибкой:", stats["failed_cities"])
    print("Файл:", args.output)


if __name__ == "__main__":
    main()
