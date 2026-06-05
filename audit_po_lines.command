#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python - << 'EOF'
import json
from value import parse_po
from pathlib import Path
from collections import defaultdict

cache = Path("po_cache")
data = json.load(open("docs/dashboard.json"))

# Build map of po_number -> list of cards
cards_by_po = defaultdict(list)
for c in data["cards"]:
    if c["po_number"]:
        cards_by_po[c["po_number"]].append(c)

print("=== POs WHERE PDF HAS MORE LINES THAN TRELLO CARDS ===")
print()
any_gap = False
for pdf in sorted(cache.glob("*.pdf")):
    po = pdf.stem
    result = parse_po(pdf)
    pdf_lines = {i["line"]: i for i in result["items"]}
    if not pdf_lines:
        continue

    trello_cards = cards_by_po.get(po, [])
    trello_line_nums = set(c["line"] for c in trello_cards if c["line"] is not None)
    missing_lines = set(pdf_lines.keys()) - trello_line_nums

    if missing_lines or len(pdf_lines) > len(trello_cards):
        pdf_total = sum(i["ext_price"] for i in pdf_lines.values())
        trello_total = sum(c["value"] or 0 for c in trello_cards)
        gap = pdf_total - trello_total
        if gap > 1:
            any_gap = True
            print(f"PO {po}:  PDF=${pdf_total:,.2f}  Trello=${trello_total:,.2f}  GAP=${gap:,.2f}")
            for ln, item in sorted(pdf_lines.items()):
                has_card = "✓" if ln in trello_line_nums else "✗ NO CARD"
                print(f"   Line {ln}: ${item['ext_price']:,.2f}  {item['description'][:40]}  {has_card}")
            print()

if not any_gap:
    print("No gaps found — every PDF line has a matching Trello card.")

print(f"TOTAL in Trello (active cards): ${data['grand_total']:,.2f}")
EOF
read -p "Press Enter to close..."
