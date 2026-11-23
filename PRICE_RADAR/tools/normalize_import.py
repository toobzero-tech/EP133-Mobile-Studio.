#!/usr/bin/env python3
"""Normalize PRICE RADAR JSON/CSV exports into one deduplicated JSON file.
Standard library only. This is an import utility, not a marketplace scraper.
"""
import argparse, csv, json, re, hashlib, io
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

def clean_url(value):
    value = (value or "").strip()
    if not value:
        return ""
    p = urlsplit(value)
    if p.scheme not in ("http", "https") or not p.netloc:
        return ""
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))

def norm_title(value):
    return re.sub(r"[^0-9a-zа-я]+", " ", (value or "").lower()).strip()

SOURCE_ALIASES = {
    "авито": "avito", "avito": "avito",
    "мешок": "meshok", "meshok": "meshok",
    "юла": "youla", "youla": "youla",
    "яндекс маркет": "yandex_market", "yandex market": "yandex_market",
    "озон": "ozon", "ozon": "ozon",
    "wildberries": "wildberries", "вайлдберриз": "wildberries",
    "днс": "dns", "dns": "dns",
    "ситилинк": "citilink", "citilink": "citilink",
    "м.видео": "mvideo", "мвидео": "mvideo", "mvideo": "mvideo",
    "эльдорадо": "eldorado", "eldorado": "eldorado",
    "мегамаркет": "megamarket", "megamarket": "megamarket",
    "manual": "manual", "ручной ввод": "manual",
}
ALLOWED_CURRENCIES = {"RUB", "RUR", "₽", "РУБ", "РУБ."}
CONDITION_ALIASES = {
    "б/у": "used", "бу": "used", "бывший в употреблении": "used",
    "новый": "new", "новое": "new", "новая": "new",
    "витринный": "open_box", "витринный образец": "open_box",
    "уценка": "open_box", "восстановленный": "refurbished",
    "реф": "refurbished", "неизвестно": "unknown",
}

def normalize(row):
    now = datetime.now(timezone.utc).isoformat()
    url = clean_url(row.get("url") or row.get("link"))
    title = (row.get("title") or row.get("name") or "").strip()
    raw_price = str(row.get("price", "")).replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        price = float(raw_price)
    except (ValueError, TypeError):
        price = 0.0
    raw_condition = (row.get("condition") or "unknown").strip().lower()
    condition = CONDITION_ALIASES.get(raw_condition, raw_condition)
    if condition not in {"new", "used", "refurbished", "open_box", "unknown"}:
        condition = "unknown"
    raw_source = (row.get("source") or row.get("marketplace") or "manual").strip().lower()
    source = SOURCE_ALIASES.get(raw_source, raw_source.replace(" ", "_"))
    currency = str(row.get("currency") or "").strip().upper()
    currency_ok = currency in ALLOWED_CURRENCIES
    country = str(row.get("country") or "").strip().upper()
    country_ok = country == "RU"
    source_id = str(row.get("source_id") or row.get("id") or "").strip()
    location = str(row.get("location") or "").strip()
    key = f"{source}:{source_id}" if source_id else (url or hashlib.sha256(
        f"{norm_title(title)}|{price}|{location}".encode()).hexdigest())
    return {
        "dedupe_key": key, "source": source, "source_id": source_id,
        "url": url, "title": title, "description": row.get("description", ""),
        "category": row.get("category", ""), "condition": condition,
        "price": price, "currency": "RUB" if currency_ok else "UNSUPPORTED",
        "country": "RU" if country_ok else "UNSUPPORTED", "location": location,
        "brand": row.get("brand", ""), "model": row.get("model", ""),
        "seller_id": row.get("seller_id", ""), "image_urls": row.get("image_urls", []),
        "published_at": row.get("published_at") or row.get("publishedAt") or "",
        "observed_at": row.get("observed_at") or row.get("observedAt") or now,
        "listing_type": (row.get("listing_type") or "fixed").lower(),
        "ends_at": row.get("ends_at") or "",
        "status": "manual_unverified" if source == "manual" else "new",
        "eligible_for_russia_feed": currency_ok and country_ok,
        "raw": row
    }

def read_rows(path):
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, list) else data.get("items", [])
    content = path.read_text(encoding="utf-8-sig")
    first = content.splitlines()[0] if content.splitlines() else ""
    return list(csv.DictReader(io.StringIO(content), delimiter=";" if first.count(";") > first.count(",") else ","))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="CSV or JSON file")
    ap.add_argument("-o", "--output", default="price_radar_normalized.json")
    args = ap.parse_args()
    rows = [normalize(r) for r in read_rows(Path(args.input))]
    unique = {}
    for row in rows:
        if not row["title"] or row["price"] <= 0 or not row["eligible_for_russia_feed"]:
            continue
        unique.setdefault(row["dedupe_key"], row)
    Path(args.output).write_text(json.dumps(list(unique.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: {len(unique)} уникальных объявлений из {len(rows)} строк -> {args.output}")

if __name__ == "__main__":
    main()
