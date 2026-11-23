#!/usr/bin/env python3
"""Extract the app's inline JavaScript and validate its syntax with Node.js."""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

html = Path(__file__).resolve().parents[1] / "index.html"
source = html.read_text(encoding="utf-8")
scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", source, flags=re.I | re.S)
if not scripts:
    raise SystemExit("No inline JavaScript block found")
# Static smoke checks for critical business rules that syntax validation alone cannot cover.
contracts = {
    "auction end-time gate": "hours<=24",
    "minimum auction discount": "m.discount>=20",
    "positive auction profit": "m.profit>0",
    "auction deal score threshold": "m.dealScore>=60",
    "completed-sale country restriction": "country!=='RU'",
    "completed-sale currency restriction": "['RUB','RUR','₽'].indexOf(currency)<0",
    "completed-sale age limit": "Date.now()-date>365*86400000",
    "UTF-8 BOM handling": "replace(/^\\uFEFF/,'')",
    "sales import deduplication": "var merged=sales.concat(valid)",
}
missing = [label for label, token in contracts.items() if token not in source]
if missing:
    raise SystemExit("Frontend smoke checks failed: " + ", ".join(missing))
node = shutil.which("node")
if not node:
    raise SystemExit("Node.js is required for frontend syntax validation")
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
    handle.write("\n".join(scripts))
    temp_path = handle.name
try:
    subprocess.run([node, "--check", temp_path], check=True)
finally:
    Path(temp_path).unlink(missing_ok=True)
print("Frontend JavaScript syntax and business-rule smoke checks: OK")
