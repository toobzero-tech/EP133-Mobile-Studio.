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
    "live offer JSON import": "$('#offersin').onchange",
    "exact active listing benchmark": "function activeMarketInfo(x)",
    "active benchmark warning label": "Активные объявления (ориентир, не цена продажи)",
    "imported offer country and currency": "country:'RU',currency:'RUB'",
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

# Exercise the real browser calculator with deterministic market data.
calc_match = re.search(r"(function calc\(x\)\{[\s\S]*?)\nfunction save", source)
if not calc_match:
    raise SystemExit("Could not isolate the frontend calc() function")
calc_source = calc_match.group(1)
harness = r"""
function n(v){const x=Number(v);return Number.isFinite(x)?x:0}
function marketInfo(x){return {market:n(x.market),confidence:n(x.confidence),count:0,source:"test"}}
""" + calc_source + r"""
const assert=require("assert");
const x={market:100000,price:60000,costs:5000,fee:5,taxFee:6,reserve:2000,confidence:80,risk:20,created:new Date().toISOString()};
const m=calc(x);
assert.strictEqual(m.profit,22000);
assert.strictEqual(m.invested,65000);
assert(Math.abs(m.roi-(22000/65000*100))<1e-9);
assert.strictEqual(m.breakEven,82000);
assert.strictEqual(m.discount,40);
assert.strictEqual(m.roiScore,Math.min(100,m.roi/50*100));
assert(m.dealScore>0 && m.dealScore<=100);
const loss=calc({...x,price:95000});
assert(loss.profit<0);
assert.strictEqual(loss.roi<0,true);
assert.strictEqual(loss.roiScore,0);
const noInvestment=calc({...x,price:0,costs:0});
assert.strictEqual(noInvestment.roi,0);
const zeroRisk=calc({...x,risk:0});
const maxRisk=calc({...x,risk:100});
assert(zeroRisk.dealScore>maxRisk.dealScore);
console.log("ROI/profit/break-even/risk calculator tests: OK");
"""
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
    handle.write(harness)
    harness_path = handle.name
try:
    subprocess.run([node, harness_path], check=True)
finally:
    Path(harness_path).unlink(missing_ok=True)


print("Frontend JavaScript syntax and business-rule smoke checks: OK")
