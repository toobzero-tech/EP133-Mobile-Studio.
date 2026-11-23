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
print("Frontend JavaScript syntax: OK")
