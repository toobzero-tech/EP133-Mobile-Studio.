#!/usr/bin/env python3
"""Non-invasive live probe for Golova.Market's documented public read API."""
import json
import urllib.parse
import urllib.request

BASE = "https://golovamarket.ru/api/public/listings"


def main():
    params = urllib.parse.urlencode({
        "city": "Москва",
        "price_currency": "RUB",
        "per_page": "5",
        "sort": "newest",
    })
    url = BASE + "?" + params
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PRICE-RADAR-source-probe/1.0 (public API)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError("HTTP " + str(response.status))
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise RuntimeError("API response exceeds 2 MB")
    payload = json.loads(raw.decode("utf-8-sig"))
    if isinstance(payload, dict):
        print("TOP_LEVEL_KEYS:", sorted(payload.keys()))
        items = payload.get("data")
        if isinstance(items, dict):
            print("DATA_KEYS:", sorted(items.keys()))
            items = items.get("data") or items.get("items")
        if not isinstance(items, list):
            items = payload.get("items") or payload.get("listings") or []
    elif isinstance(payload, list):
        items = payload
        print("TOP_LEVEL_TYPE: list")
    else:
        raise RuntimeError("Unexpected JSON response type: " + type(payload).__name__)
    print("ITEM_COUNT:", len(items))
    if items:
        sample = items[0]
        if not isinstance(sample, dict):
            raise RuntimeError("Listing record is not an object")
        print("SAMPLE_KEYS:", sorted(sample.keys()))
        print("SAMPLE:", json.dumps(sample, ensure_ascii=False)[:6000])
    else:
        print("NO_LISTINGS_FOR_MOSCOW_QUERY")
    print("PROBE_OK")


if __name__ == "__main__":
    main()
