#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python - << 'EOF'
from value import extract_text, parse_po_text
from pathlib import Path

pdf = Path("po_cache/385902.pdf")
text = extract_text(pdf)
lines = [s.strip() for s in text.splitlines()]

# Find where lines 9, 10, 11 appear in the raw text
print("=== RAW TEXT AROUND LINE 9/10/11 ===")
for i, line in enumerate(lines):
    if line in ("9", "10", "11") or "HEADER" in line:
        # show context around it
        start = max(0, i-3)
        end = min(len(lines), i+10)
        print(f"\n--- around index {i} (value='{line}') ---")
        for j in range(start, end):
            print(f"  [{j}] {repr(lines[j])}")

print()
print("=== RAW TEXT AROUND LINE 18/19/20 ===")
for i, line in enumerate(lines):
    if line in ("18", "19", "20"):
        start = max(0, i-3)
        end = min(len(lines), i+10)
        print(f"\n--- around index {i} (value='{line}') ---")
        for j in range(start, end):
            print(f"  [{j}] {repr(lines[j])}")

print()
result = parse_po_text(text)
print(f"Parsed lines: {[i['line'] for i in result['items']]}")
print(f"Total: ${sum(i['ext_price'] for i in result['items']):,.2f}")
for it in result['items']:
    print(f"  Line {it['line']}: qty={it['qty']} x ${it['unit_price']} = ${it['ext_price']:,.2f}  {it['description'][:40]}")
EOF
read -p "Press Enter to close..."
