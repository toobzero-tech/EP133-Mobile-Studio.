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
        summaries = []
        for item in items[:5]:
            if isinstance(item, dict):
                summaries.append({
                    "slug": item.get("slug"),
                    "title": item.get("title"),
                    "price": item.get("price"),
                    "currency": item.get("currency"),
                    "city": item.get("city"),
                    "type": item.get("type"),
                    "condition": item.get("condition"),
                })
        print("SAMPLE_SUMMARIES:", json.dumps(summaries, ensure_ascii=False))
        sample = next((x for x in items if isinstance(x, dict) and x.get("slug")), None)
        if sample:
            detail_url = "https://golovamarket.ru/api/public/listings/" + urllib.parse.quote(str(sample["slug"]), safe="")
            detail_req = urllib.request.Request(detail_url, headers={"User-Agent": "PRICE-RADAR-source-probe/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(detail_req, timeout=20) as detail_response:
                detail = json.loads(detail_response.read(2_000_001).decode("utf-8-sig"))
            if isinstance(detail, dict):
                print("DETAIL_TOP_LEVEL_KEYS:", sorted(detail.keys()))
                detail_obj = detail.get("data") if isinstance(detail.get("data"), dict) else detail
                print("DETAIL_KEYS:", sorted(detail_obj.keys()) if isinstance(detail_obj, dict) else type(detail_obj).__name__)
                if isinstance(detail_obj, dict):
                    print("DETAIL_SAFE_SAMPLE:", json.dumps({k:v for k,v in detail_obj.items() if k not in {"images","cover","seller","description"}}, ensure_ascii=False)[:4000])
    else:
        print("NO_LISTINGS_FOR_MOSCOW_QUERY")
    print("PROBE_OK")


if __name__ == "__main__":
    main()
