#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python - << 'EOF'
import json, sys
from value import parse_po
from pathlib import Path

# Cards that are line_not_found_in_po
failing = [
    ("385503", 1), ("385503", 2),
    ("384930", 1), ("384346", 1),
    ("383649", 2), ("385384", 1),
    ("385971", 1), ("385902", 10), ("385902", 19),
    ("385801", 1), ("385771", 1), ("382015", 2),
]

cache = Path("po_cache")
for po, line in failing:
    pdf = cache / f"{po}.pdf"
    if not pdf.exists():
        print(f"PO {po}: PDF not cached")
        continue
    result = parse_po(pdf)
    found_lines = [i["line"] for i in result["items"]]
    status = "✓" if line in found_lines else "✗ MISSING"
    print(f"PO {po} Line {line}: {status}  — PDF has lines: {found_lines}")

print()
print("--- Cards with no Line number in name ---")
data = json.load(open("docs/dashboard.json"))
no_line = [c for c in data["cards"] if c["status"] == "no_po_number_in_name" and "SUN PO" in c["name"]]
for c in no_line:
    print(f"  {c['name']}")
EOF
read -p "Press Enter to close..."
