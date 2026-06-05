#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python - << 'EOF'
from value import extract_text
from pathlib import Path

for po in ["385801", "382818", "384028"]:
    pdf = Path(f"po_cache/{po}.pdf")
    if not pdf.exists():
        print(f"PO {po}: not cached")
        continue
    text = extract_text(pdf)
    print(f"=== PO {po} ({len(text)} chars) ===")
    # Show first 800 chars
    print(text[:800])
    print("...")
    print()
EOF
read -p "Press Enter to close..."
