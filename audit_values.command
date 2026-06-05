#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python - << 'EOF'
import json
from value import parse_po, extract_text
from pathlib import Path

cache = Path("po_cache")

# Load dashboard to get current card values
data = json.load(open("docs/dashboard.json"))

print("=== CARDS WITH VALUES (spot check) ===")
valued = [c for c in data["cards"] if c["value"] is not None]
for c in valued[:20]:
    print(f"  ${c['value']:>9,.2f}  qty={c['qty']}  unit=${c['unit_price']}  | {c['name'][:55]}")

print()
print("=== RAW PDF PARSE (first 5 cached POs) ===")
for pdf in sorted(cache.glob("*.pdf"))[:8]:
    po = pdf.stem
    result = parse_po(pdf)
    items = result["items"]
    if not items:
        print(f"  PO {po}: NO ITEMS PARSED")
        continue
    total = sum(i["ext_price"] for i in items)
    print(f"  PO {po}: {len(items)} item(s), total=${total:,.2f}")
    for it in items:
        calc = round(it["unit_price"] * it["qty"], 2)
        match = "✓" if abs(calc - it["ext_price"]) < 0.02 else f"✗ calc={calc}"
        print(f"    Line {it['line']}: qty={it['qty']} x ${it['unit_price']} = ${it['ext_price']} {match}  part={it['part']}")

print()
print(f"=== GRAND TOTAL: ${data['grand_total']:,.2f} across {data['card_count']} cards ===")
print(f"    Missing values: {data['missing_count']} cards")
EOF
read -p "Press Enter to close..."
