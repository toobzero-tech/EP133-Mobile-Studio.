import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

API_URL = "https://api.api.sh/avito/v1/search"
API_TIMEOUT = 35

app = FastAPI(title="PRICE RADAR API", version="0.1.0")

origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _allowed_avito_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
        return parsed.scheme == "https" and parsed.hostname in {"avito.ru", "www.avito.ru"}
    except (TypeError, ValueError):
        return False


def _normalise_listing(item: dict[str, Any]) -> dict[str, Any] | None:
    url = item.get("url") or item.get("link")
    if not isinstance(url, str) or not _allowed_avito_url(url):
        return None

    currency = str(item.get("currency") or "").upper()
    if currency != "RUB":
        return None

    try:
        price = float(item.get("price"))
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    images = item.get("images") or []
    category = item.get("category")
    if isinstance(category, dict):
        category = category.get("name") or category.get("slug")
    return {
        "id": str(item.get("id") or ""),
        "source": "avito",
        "url": url,
        "title": str(item.get("title") or "").strip(),
        "description": str(item.get("description") or "").strip(),
        "price": price,
        "currency": "RUB",
        "published_at": item.get("published") or item.get("published_at"),
        "location": item.get("location") or item.get("address"),
        "category": category,
        "params": item.get("params"),
        "images": [x for x in images if isinstance(x, str) and x.startswith("https://")],
        "seller": item.get("seller") if isinstance(item.get("seller"), dict) else {},
        "condition": item.get("condition") or item.get("params"),
        "delivery": item.get("delivery"),
        "reserved": item.get("reserved"),
    }


def call_apish(params: dict[str, str]) -> dict[str, Any]:
    key = os.getenv("APISH_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="API.SH не настроен: добавьте APISH_API_KEY в переменные окружения сервера.",
        )

    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        API_URL + "?" + query,
        headers={"x-api-key": key, "Accept": "application/json", "User-Agent": "PRICE-RADAR/0.1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
            payload = json.loads(response.read(8 * 1024 * 1024).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # API.SH documents 404 for a valid search with no matching listings.
        if exc.code == 404:
            return {"total": 0, "count": 0, "page": int(params.get("page", "1")), "next_page": None, "listings": [], "credits_used": 5}
        if exc.code in (401, 403):
            raise HTTPException(status_code=502, detail="API.SH отклонил ключ или доступ.") from exc
        raise HTTPException(status_code=502, detail=f"Ошибка API.SH: HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Не удалось получить корректный ответ от API.SH.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="API.SH вернул неожиданный формат данных.")
    if payload.get("success") is False:
        raise HTTPException(status_code=502, detail="API.SH сообщил об ошибке поиска.")
    return payload


@app.get("/")
def index() -> FileResponse:
    page = Path(__file__).resolve().parents[1] / "index.html"
    return FileResponse(page)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "price-radar-api",
        "apish_configured": bool(os.getenv("APISH_API_KEY", "").strip()),
    }


@app.get("/api/search")
def search_avito(
    q: str | None = Query(default=None, max_length=180),
    category: str | None = Query(default=None, max_length=180),
    url: str | None = Query(default=None, max_length=1000),
    location: str = Query(default="rossiya", max_length=100),
    price_min: int | None = Query(default=None, ge=0),
    price_max: int | None = Query(default=None, ge=1),
    condition: str | None = Query(default=None, pattern="^(new|used)$"),
    with_photos: bool = Query(default=True),
    seller_type: str | None = Query(default=None, pattern="^(private|company|all)$"),
    sort: str = Query(default="newest", pattern="^(default|price_asc|price_desc|newest|discount)$"),
    page: int = Query(default=1, ge=1, le=100),
) -> dict[str, Any]:
    if not any((q and q.strip(), category and category.strip(), url and url.strip())):
        raise HTTPException(status_code=422, detail="Укажите q, category или ссылку url на поиск Avito.")
    if url and not _allowed_avito_url(url):
        raise HTTPException(status_code=422, detail="Разрешены только HTTPS-ссылки avito.ru.")

    params: dict[str, str] = {"location": location, "sort": sort, "page": str(page)}
    if q and q.strip():
        params["q"] = q.strip()
    if category and category.strip():
        params["category"] = category.strip()
    if url and url.strip():
        params["url"] = url.strip()
        params.pop("location", None)
    if price_min is not None:
        params["price_min"] = str(price_min)
    if price_max is not None:
        params["price_max"] = str(price_max)
    if condition:
        params["condition"] = condition
    if with_photos:
        params["with_photos"] = "true"
    if seller_type:
        params["seller_type"] = seller_type

    payload = call_apish(params)
    source_rows = payload.get("listings") or []
    if not isinstance(source_rows, list):
        raise HTTPException(status_code=502, detail="В ответе API.SH отсутствует массив listings.")
    listings = [_normalise_listing(x) for x in source_rows if isinstance(x, dict)]
    listings = [x for x in listings if x is not None and x["title"]]

    return {
        "source": "avito",
        "query": {"q": q, "category": category, "location": location, "page": page},
        "total": int(payload.get("total") or 0),
        "count": len(listings),
        "page": int(payload.get("page") or page),
        "next_page": payload.get("next_page"),
        "credits_used": payload.get("credits_used"),
        "fetched_at": payload.get("fetched_at"),
        "listings": listings,
    }
