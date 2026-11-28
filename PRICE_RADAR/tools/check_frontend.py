#!/usr/bin/env python3
"""Validate the Avito-only PRICE RADAR frontend contract and JavaScript syntax."""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script[^>]*>(.*?)</script>", source, flags=re.I | re.S)
if not scripts:
    raise SystemExit("No inline JavaScript block found")

contracts = {
    "Avito-only product identity": "только Avito",
    "live backend search": 'fetch("/api/search?"',
    "newest-first ordering": 'sort:"newest"',
    "original Avito listing link": "Открыть объявление на Avito",
    "safe external link": 'rel="noopener noreferrer"',
    "real listing publication date": "published_at",
    "real source credit reporting": "credits_used",
    "pagination": "next_page",
    "no fake profit claims": "не подтверждённые сделки",
    "Gemini analysis action": "Анализ ИИ",
    "Avito comparable analysis": "renderComparison",
    "private access login": 'id="accessPanel"',
    "server token header": "X-Price-Radar-Token",
    "session-only access token": "sessionStorage.setItem",
}
missing = [label for label, token in contracts.items() if token not in source]
if missing:
    raise SystemExit("Frontend contract checks failed: " + ", ".join(missing))

for forbidden in ("Wildberries", "Ozon", "Яндекс Маркет", "М.Видео", "Голова.Маркет"):
    if forbidden.lower() in source.lower():
        raise SystemExit("Non-Avito source still present in frontend: " + forbidden)


render_config = (root.parent / "render.yaml").read_text(encoding="utf-8")
render_contracts = {
    "Render root includes frontend": "rootDir: PRICE_RADAR",
    "Render installs backend requirements": "buildCommand: pip install -r backend/requirements.txt",
    "Render starts backend package": "startCommand: uvicorn backend.app:app",
}
missing_render = [label for label, token in render_contracts.items() if token not in render_config]
if missing_render:
    raise SystemExit("Render deployment checks failed: " + ", ".join(missing_render))

node = shutil.which("node")
if not node:
    raise SystemExit("Node.js is required for frontend syntax validation")

with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
    handle.write(chr(10).join(scripts))
    temp_path = handle.name
try:
    subprocess.run([node, "--check", temp_path], check=True)
finally:
    Path(temp_path).unlink(missing_ok=True)

print("Avito-only frontend contract and JavaScript syntax: OK")
