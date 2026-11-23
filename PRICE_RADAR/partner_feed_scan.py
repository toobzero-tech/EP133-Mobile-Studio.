#!/usr/bin/env python3
"""PRICE RADAR partner feed collector. Public, owner-authorized HTTPS feeds only."""
from __future__ import annotations
import csv, datetime as dt, json, os, re, sys, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
CONFIG = Path(os.getenv("PRICE_RADAR_FEEDS", ROOT / "partner-feeds.json"))
OUT = Path(os.getenv("PRICE_RADAR_OUT", ROOT / "partner_feed_offers.json"))
UA = "PriceRadar/0.7 (+authorized-public-feed-import)"
MAX_BYTES = 12 * 1024 * 1024
TIMEOUT = 20

def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()

def get_path(obj, path):
    cur = obj
    for part in str(path or "").split("."):
        if not part: continue
        if isinstance(cur, list):
            try: cur = cur[int(part)]
            except (ValueError, IndexError): return None
        elif isinstance(cur, dict): cur = cur.get(part)
        else: return None
    return cur

def fetch(url):
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Only public HTTPS feed URLs are accepted")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, application/xml, text/xml, application/rss+xml, application/atom+xml"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        if response.status != 200: raise ValueError(f"HTTP {response.status}")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES: raise ValueError("Feed exceeds 12 MiB limit")
    return data

def clean_offer(raw, source, location, fixed_currency=None):
    title = str(raw.get("title") or raw.get("name") or "").strip()
    url = str(raw.get("url") or raw.get("link") or raw.get("product_url") or "").strip()
    price_raw = raw.get("price") or raw.get("price_value")
    currency = str(fixed_currency or raw.get("currency") or raw.get("currencyId") or "").upper()
    country = str(raw.get("country") or raw.get("country_code") or "RU").upper()
    try: price = float(str(price_raw).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError): return None
    if not title or not re.match(r"^https://", url, re.I) or price <= 0 or currency not in ("RUB", "RUR", "₽") or country not in ("RU", "RUS", "РОССИЯ"):
        return None
    condition = str(raw.get("condition") or "unknown").lower()
    if condition not in ("new", "used", "open_box", "refurbished", "unknown", "б/у", "новый"):
        condition = "unknown"
    return {
        "source": source, "source_id": str(raw.get("source_id") or raw.get("id") or raw.get("sku") or url),
        "title": title, "url": url, "price": round(price, 2), "currency": "RUB", "country": "RU",
        "location": str(raw.get("location") or raw.get("city") or location or "Россия"),
        "category": str(raw.get("category") or ""), "brand": str(raw.get("brand") or ""),
        "model": str(raw.get("model") or raw.get("sku") or ""),
        "condition": condition, "published_at": str(raw.get("published_at") or raw.get("pubDate") or ""),
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "eligible_for_russia_feed": True, "raw": {"type": "sale"}
    }

def parse_json(data, cfg):
    doc = json.loads(data.decode("utf-8-sig"))
    items = get_path(doc, cfg.get("items_path", "items"))
    if items is None and isinstance(doc, list): items = doc
    if not isinstance(items, list): raise ValueError("Configured JSON items_path did not resolve to an array")
    fields = cfg.get("fields", {})
    out=[]
    for item in items:
        if not isinstance(item, dict): continue
        mapped={key:get_path(item, path) for key,path in fields.items()}
        if cfg.get("currency_constant"): mapped["currency"] = cfg["currency_constant"]
        if cfg.get("country_constant"): mapped["country"] = cfg["country_constant"]
        x=clean_offer(mapped, cfg.get("source","partner_json"), cfg.get("location","Россия"))
        if x: out.append(x)
    return out

def parse_xml(data, cfg, kind):
    root=ET.fromstring(data)
    out=[]
    if kind == "yml":
        for offer in root.iter():
            if local_name(offer.tag) != "offer" or offer.attrib.get("available","true").lower() != "true": continue
            fields={local_name(c.tag): (c.text or "").strip() for c in offer}
            currency=fields.get("currencyid","")
            raw={"title":fields.get("name") or fields.get("model") or fields.get("typeprefix"),"url":fields.get("url"),"price":fields.get("price"),"currency":currency,"country":"RU","category":fields.get("categoryid"),"brand":fields.get("vendor"),"model":fields.get("model"),"source_id":offer.attrib.get("id")}
            x=clean_offer(raw,cfg.get("source","partner_yml"),cfg.get("location","Россия"))
            if x: out.append(x)
    else:
        for node in root.iter():
            tag=local_name(node.tag)
            if tag not in ("item","entry"): continue
            fields={local_name(c.tag):(c.text or "").strip() for c in node}
            link=fields.get("link","")
            if not link:
                for c in node:
                    if local_name(c.tag)=="link": link=c.attrib.get("href","")
            raw={"title":fields.get("title"),"url":link,"price":fields.get("price") or fields.get("price:amount"),"currency":fields.get("currency") or fields.get("price:currency"),"country":"RU","category":fields.get("category"),"brand":fields.get("brand"),"model":fields.get("model"),"published_at":fields.get("pubdate") or fields.get("published"),"source_id":fields.get("guid") or fields.get("id")}
            x=clean_offer(raw,cfg.get("source","partner_rss"),cfg.get("location","Россия"))
            if x: out.append(x)
    return out

def main():
    if not CONFIG.exists():
        print(f"No feed config: {CONFIG}; create it from partner-feeds.example.json")
        OUT.write_text(json.dumps({"offers":[],"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"sources":[]},ensure_ascii=False,indent=2),encoding="utf-8")
        return
    cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
    all_rows=[]; report=[]
    for group,kind in (("json_feeds","json"),("yml_feeds","yml"),("rss_atom_feeds","rss")):
        for feed in cfg.get(group,[]):
            if not feed.get("enabled"): continue
            if not feed.get("country_confirmed") or (kind=="json" and not (feed.get("currency_confirmed") or feed.get("currency_constant"))):
                report.append({"source":feed.get("source"),"status":"skipped","reason":"country/currency confirmation missing"}); continue
            try:
                payload=fetch(feed["url"])
                rows=parse_json(payload,feed) if kind=="json" else parse_xml(payload,feed,kind)
                all_rows.extend(rows)
                report.append({"source":feed.get("source"),"status":"ok","accepted":len(rows)})
            except Exception as exc:
                report.append({"source":feed.get("source"),"status":"error","reason":str(exc)[:240]})
    dedup={}
    for row in all_rows: dedup.setdefault(row["url"].rstrip("/"),row)
    result={"version":1,"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"country":"RU","currency":"RUB","offers":list(dedup.values()),"sources":report}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"offers":len(dedup),"sources":report},ensure_ascii=False))
if __name__=="__main__": main()
