"""Private, stateless multimodal listing analysis via Google's Gemini Interactions API."""
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

GEMINI_TIMEOUT = 55
MAX_IMAGE_BYTES = 2_500_000
ALLOWED_IMAGE_SUFFIXES = (".avito.st", ".avito.ru", ".avito.net")
INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


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
            return {"type": "image", "mime_type": mime, "data": base64.b64encode(data).decode("ascii")}
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _extract_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    chunks: list[str] = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("text"), str):
                chunks.append(item["text"])
            content = item.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        chunks.append(part["text"])
    if chunks:
        return "\n".join(chunks).strip()
    raise RuntimeError("Gemini вернул ответ без текстового результата.")


def _parse_json_text(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$", "", text, flags=re.IGNORECASE)
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini вернул ответ не в ожидаемом JSON-формате.") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Gemini вернул неожиданный формат анализа.")
    return result


def _call_interactions(parts: list[dict[str, Any]], model: str, key: str, max_output_tokens: int = 1200) -> dict[str, Any]:
    body = {
        "model": model,
        "input": parts,
        "store": False,
        "generation_config": {"temperature": 0.1, "max_output_tokens": max_output_tokens},
    }
    request = urllib.request.Request(
        INTERACTIONS_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-goog-api-key": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Api-Revision": "2026-05-20",
        },
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
    if not isinstance(payload, dict):
        raise RuntimeError("Gemini вернул неожиданный формат данных.")
    return _parse_json_text(_extract_output_text(payload))


def analyze_listing(listing: dict[str, Any]) -> dict[str, Any]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Gemini не настроен: добавьте GEMINI_API_KEY в переменные окружения сервера.")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    title = str(listing.get("title") or "")[:300]
    description = str(listing.get("description") or "")[:5000]
    params = str(listing.get("params") or "")[:2000]
    prompt = (
        "Ты эксперт по идентификации подержанных товаров и поиску скрытой ценности для перепродажи на Avito. "
        "Проанализируй только факты из объявления и приложенных фотографий. "
        "Не выдумывай производителя, модель, материал, редкость, комплектность или рыночные цены. "
        "Если точная идентификация не подтверждается, явно укажи неопределённость. "
        "Подготовь короткий search_query для поиска максимально точных аналогов на Avito: "
        "название модели/предмета и ключевой вариант, без слов 'купить', 'продам', 'дешево'. "
        "Если предмет нельзя надёжно определить, search_query оставь пустым. "
        "Верни только JSON с полями: identification (string), likely_brand_model (string), "
        "material_or_variant (string), clues (array of strings), uncertainty (array of strings), "
        "risk_flags (array of strings), completeness_questions (array of strings), "
        "resale_potential (low|medium|high|unknown), resale_reason (string), "
        "search_query (string), next_checks (array of strings). "
        "Не указывай рыночную стоимость: аналоги ещё не проверены. Язык ответа: русский.\n\n"
        f"Заголовок: {title}\nОписание: {description}\nПараметры: {params}\n"
        f"Цена объявления: {listing.get('price')} RUB\nМестоположение: {str(listing.get('location') or '')[:200]}"
    )
    parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    images = listing.get("images") if isinstance(listing.get("images"), list) else []
    used_images = 0
    for url in images[:3]:
        if isinstance(url, str):
            part = _image_part(url)
            if part:
                parts.append(part)
                used_images += 1
    result = _call_interactions(parts, model, key)
    result["images_analyzed"] = used_images
    result["model"] = model
    result["market_value_min"] = None
    result["market_value_max"] = None
    return result


def compare_listing(listing: dict[str, Any], analysis: dict[str, Any], comparables: list[dict[str, Any]]) -> dict[str, Any]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Gemini не настроен.")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    candidates = []
    for item in comparables[:15]:
        candidates.append({
            "id": str(item.get("id") or ""),
            "title": str(item.get("title") or "")[:240],
            "price": item.get("price"),
            "description": str(item.get("description") or "")[:500],
            "params": str(item.get("params") or "")[:300],
            "condition": str(item.get("condition") or "")[:100],
            "seller_type": str((item.get("seller") or {}).get("type") or ""),
            "url": str(item.get("url") or ""),
        })
    prompt = (
        "Сопоставь исходный лот с реальными кандидатами из Avito. Выбери только те ID, "
        "которые относятся к тому же предмету, модели, поколению и сопоставимой комплектации. "
        "Исключи аксессуары, запчасти, похожие, но другие модели, оптовые лоты и явно нерелевантные товары. "
        "Не выдумывай цены и ID. Если подходящих аналогов нет, верни пустой comparable_ids. "
        "Верни только JSON: comparable_ids (array of exact string IDs), confidence (0-100 integer), "
        "reason (string), caveats (array of strings). Не рассчитывай стоимость самостоятельно.\n\n"
        f"Исходный лот: {json.dumps({'title': listing.get('title'), 'price': listing.get('price'), 'description': listing.get('description'), 'params': listing.get('params'), 'ai_identification': analysis.get('identification'), 'brand_model': analysis.get('likely_brand_model'), 'variant': analysis.get('material_or_variant')}, ensure_ascii=False)}\n"
        f"Кандидаты Avito: {json.dumps(candidates, ensure_ascii=False)}"
    )
    result = _call_interactions([{"type": "text", "text": prompt}], model, key, max_output_tokens=900)
    ids = result.get("comparable_ids")
    valid_ids = {x["id"] for x in candidates if x["id"]}
    result["comparable_ids"] = [str(x) for x in ids if str(x) in valid_ids] if isinstance(ids, list) else []
    result["confidence"] = max(0, min(100, int(result.get("confidence") or 0)))
    result["model"] = model
    return result
