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

def normalize(row):
    now = datetime.now(timezone.utc).isoformat()
    url = clean_url(row.get("url") or row.get("link"))
    title = (row.get("title") or row.get("name") or "").strip()
    try:
        price = float(str(row.get("price", "")).replace(" ", "").replace(",", "."))
    except ValueError:
        price = 0.0
    condition = (row.get("condition") or "unknown").lower()
    aliases = {"б/у":"used", "бу":"used", "новый":"new", "новое":"new"}
    condition = aliases.get(condition, condition)
    source = (row.get("source") or row.get("marketplace") or "manual").strip().lower()
    source_id = str(row.get("source_id") or row.get("id") or "").strip()
    key = f"{source}:{source_id}" if source_id else (url or hashlib.sha256(
        f"{norm_title(title)}|{price}|{row.get('location','')}".encode()).hexdigest())
    return {
        "dedupe_key": key, "source": source, "source_id": source_id,
        "url": url, "title": title, "description": row.get("description", ""),
        "category": row.get("category", ""), "condition": condition,
        "price": price, "currency": row.get("currency") or "RUB",
        "location": row.get("location", ""),
        "published_at": row.get("published_at") or "",
        "observed_at": row.get("observed_at") or now,
        "status": "manual_unverified" if source == "manual" else "new",
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
        if not row["title"] or row["price"] <= 0:
            continue
        unique.setdefault(row["dedupe_key"], row)
    Path(args.output).write_text(json.dumps(list(unique.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: {len(unique)} уникальных объявлений из {len(rows)} строк -> {args.output}")

if __name__ == "__main__":
    main()
