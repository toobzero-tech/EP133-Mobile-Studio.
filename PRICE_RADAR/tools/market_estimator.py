#!/usr/bin/env python3
"""Estimate Russian-market prices from explicitly completed comparable sales.

No scraping and no external dependencies. Only exact normalized brand/model and
condition matches are accepted; active listings are never treated as sales.
"""
import argparse
import json
import re
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path


def key(value):
    return re.sub(r"[^0-9a-zа-я]+", "", str(value or "").lower())


def condition(value):
    aliases = {
        "б/у": "used", "бу": "used", "used": "used",
        "новый": "new", "new": "new",
        "витринный образец": "open_box", "open_box": "open_box",
        "восстановленный": "refurbished", "refurbished": "refurbished",
        "неизвестно": "unknown", "unknown": "unknown",
    }
    raw = str(value or "unknown").strip().lower()
    return aliases.get(raw, raw)


def parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def estimate(listings, sales, now=None, max_age_days=365):
    now = now or datetime.now(timezone.utc)
    prepared = []
    for sale in sales:
        status = str(sale.get("status", "")).lower()
        if status not in {"sold", "completed", "finished"}:
            continue
        if str(sale.get("country", "")).upper() != "RU":
            continue
        if str(sale.get("currency", "")).upper() not in {"RUB", "RUR", "₽"}:
            continue
        amount = sale.get("sold_price", sale.get("price"))
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        sold_at = parse_date(sale.get("sold_at") or sale.get("completed_at"))
        if not sold_at or sold_at > now or (now - sold_at) > timedelta(days=max_age_days):
            continue
        brand_key, model_key = key(sale.get("brand")), key(sale.get("model"))
        if not brand_key or not model_key:
            continue
        prepared.append((brand_key, model_key, condition(sale.get("condition")), amount, sold_at, sale))

    output = []
    for listing in listings:
        brand_key, model_key = key(listing.get("brand")), key(listing.get("model"))
        cond = condition(listing.get("condition"))
        matches = [x for x in prepared if x[0] == brand_key and x[1] == model_key and x[2] == cond]
        prices = [x[3] for x in matches]
        if not prices:
            output.append({
                "listing_id": listing.get("id", ""),
                "market_estimate": None,
                "comparable_count": 0,
                "confidence": 0,
                "method": "no_exact_completed_sales",
                "spread_iqr_pct": None,
                "comparable_urls": [],
            })
            continue
        median = statistics.median(prices)
        quartiles = statistics.quantiles(prices, n=4, method="inclusive") if len(prices) >= 2 else [median, median, median]
        spread = ((quartiles[2] - quartiles[0]) / median * 100) if median else 0
        count = len(prices)
        confidence = 25 if count == 1 else 45 if count == 2 else 65 if count < 5 else 80
        newest = max(x[4] for x in matches)
        age_days = (now - newest).total_seconds() / 86400
        if age_days > 180:
            confidence -= 15
        elif age_days > 90:
            confidence -= 8
        if spread > 50:
            confidence -= 20
        elif spread > 30:
            confidence -= 10
        confidence = max(0, min(90, confidence))
        urls = [x[5].get("url", "") for x in sorted(matches, key=lambda x: x[4], reverse=True) if x[5].get("url")]
        output.append({
            "listing_id": listing.get("id", ""),
            "market_estimate": round(median, 2),
            "comparable_count": count,
            "confidence": confidence,
            "method": "median_exact_brand_model_condition_completed_sales",
            "spread_iqr_pct": round(spread, 1),
            "comparable_urls": urls[:10],
        })
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="JSON with listings and completed_sales arrays")
    parser.add_argument("-o", "--output", default="price_radar_estimates.json")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    results = estimate(data.get("listings", []), data.get("completed_sales", []))
    Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: оценок {sum(x['market_estimate'] is not None for x in results)} из {len(results)} объявлений")


if __name__ == "__main__":
    main()
