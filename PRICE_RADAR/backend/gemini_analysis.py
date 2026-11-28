"""Optional Gemini analysis for Avito listings. API keys stay server-side."""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

GEMINI_TIMEOUT = 55
MAX_IMAGE_BYTES = 2_500_000
ALLOWED_IMAGE_SUFFIXES = (".avito.st", ".avito.ru", ".avito.net")


def _safe_image_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
        host = (parsed.hostname or "").lower()
        return parsed.scheme == "https" and any(host == suffix[1:] or host.endswith(suffix) for suffix in ALLOWED_IMAGE_SUFFIXES)
    except (TypeError, ValueError):
        return False


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _safe_image_url(newurl):
            raise urllib.error.HTTPError(newurl, code, "Blocked image redirect outside Avito CDN", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _image_part(url: str) -> dict[str, Any] | None:
    if not _safe_image_url(url):
        return None
    opener = urllib.request.build_opener(_SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "PRICE-RADAR/0.1", "Accept": "image/jpeg,image/png,image/webp"})
    try:
        with opener.open(request, timeout=12) as response:
            if not _safe_image_url(response.geturl()):
                return None
            mime = response.headers.get_content_type()
            if mime not in {"image/jpeg", "image/png", "image/webp"}:
                return None
            data = response.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                return None
            return {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode("ascii")}}
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def analyze_listing(listing: dict[str, Any]) -> dict[str, Any]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Gemini не настроен: добавьте GEMINI_API_KEY в переменные окружения сервера.")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    title = str(listing.get("title") or "")[:300]
    description = str(listing.get("description") or "")[:5000]
    params = str(listing.get("params") or "")[:2000]
    prompt = (
        "Ты эксперт по идентификации подержанных товаров и поиску скрытой ценности для перепродажи. "
        "Проанализируй только факты из объявления и приложенных фотографий. "
        "Не выдумывай производителя, модель, материал, редкость, комплектность или рыночные цены. "
        "Если точная идентификация не подтверждается, явно укажи неопределённость. "
        "Не называй товар выгодным без сравнения с реальными аналогами. "
        "Верни только JSON с полями: identification (string), likely_brand_model (string), "
        "material_or_variant (string), clues (array of strings), uncertainty (array of strings), "
        "risk_flags (array of strings), completeness_questions (array of strings), "
        "resale_potential (low|medium|high|unknown), resale_reason (string), "
        "market_value_min (null), market_value_max (null), next_checks (array of strings). "
        "Поля market_value_min и market_value_max всегда null: аналоги ещё не проверены. "
        "Язык ответа: русский.\n\n"
        f"Заголовок: {title}\nОписание: {description}\nПараметры: {params}\n"
        f"Цена объявления: {listing.get('price')} RUB\nМестоположение: {str(listing.get('location') or '')[:200]}"
    )
    parts: list[dict[str, Any]] = [{"text": prompt}]
    images = listing.get("images") if isinstance(listing.get("images"), list) else []
    used_images = 0
    for url in images[:3]:
        if isinstance(url, str):
            part = _image_part(url)
            if part:
                parts.append(part)
                used_images += 1

    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1200,
            "responseMimeType": "application/json",
        },
    }
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"x-goog-api-key": key, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=GEMINI_TIMEOUT) as response:
            payload = json.loads(response.read(2_000_000).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError("Gemini отклонил ключ или доступ.") from exc
        if exc.code == 429:
            raise RuntimeError("Gemini временно ограничил запросы или исчерпана квота.") from exc
        raise RuntimeError(f"Ошибка Gemini API: HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("Не удалось получить корректный ответ от Gemini.") from exc

    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini вернул ответ не в ожидаемом JSON-формате.") from exc

    if not isinstance(result, dict):
        raise RuntimeError("Gemini вернул неожиданный формат анализа.")
    result["images_analyzed"] = used_images
    result["model"] = model
    # Prevent a model response from inventing a market estimate before comparables exist.
    result["market_value_min"] = None
    result["market_value_max"] = None
    return result
