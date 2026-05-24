"""Parse Sun Automation PO PDFs into per-line $ values.

Pure functions, no IO. The parser keys off the column-header sequence
that anchors every line item on a Sun Automation PO:

    Line
    Sun Part Number/Rev/Description
    Order Qty
    Unit Price
    Ext Price
    Ven Part
    {line_n}
    {UOM}                    # usually "EA"
    {unit_price}/{per_uom}   # e.g. "275.00/1"
    {ext_price}              # extended (unit * qty)
    {qty}
    {part}  /  {rev}  /  {description}   # description may span multiple lines

Multi-line POs repeat the header block per line item. Lines may be skipped
(POs are sometimes edited so line numbers aren't contiguous) — we just
take whatever's there.

Used by ``update_dashboard.py`` to compute the $ value of each Trello card.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable


PART_LINE_RE = re.compile(
    r"^(?P<part>[\w\-]+)\s*/\s*(?P<rev>[\w\-]+)\s*/\s*(?P<desc>.+?)\s*$"
)
PRICE_PER_RE = re.compile(r"^(?P<unit>\d+\.\d{2})\s*/\s*\d+\s*$")
NUMBER_RE = re.compile(r"^(?P<n>\d+(?:\.\d+)?)\s*$")
PONUM_RE = re.compile(r"PO Number:\s*\n\s*(\d+)", re.MULTILINE)

# Column-header rows that mark the start of each line-item block.
HEADER_ROWS = (
    "Line",
    "Sun Part Number/Rev/Description",
    "Order Qty",
    "Unit Price",
    "Ext Price",
)
# Where the data-row block ends so we know when to stop slurping the
# description into part_line.
LINE_TERMINATORS = ("- Shipping Release Requirement -", "Line")


@dataclass
class LineItem:
    line: int
    part: str          # raw part number as printed on PO (may have dashes)
    part_digits: str   # digits-only normalized form for matching Trello fields
    rev: str
    description: str
    qty: float
    unit_price: float
    ext_price: float
    uom: str


def normalize_part(raw: str) -> str:
    """Strip dashes/underscores so PO parts match Trello custom-field parts.

    Sun POs decorate part numbers with dashes (e.g. ``---113241--``) but the
    Trello "Part #" field stores the digits-only canonical form. The intake
    workflow already normalizes this; we mirror it here.
    """
    return re.sub(r"[^A-Za-z0-9]", "", raw or "")


def extract_text(pdf_bytes_or_path) -> str:
    """Return the full concatenated text of every page. Lazy-imports PyMuPDF."""
    import fitz  # PyMuPDF — kept local so test code doesn't need it at import-time
    if isinstance(pdf_bytes_or_path, (bytes, bytearray)):
        doc = fitz.open(stream=bytes(pdf_bytes_or_path), filetype="pdf")
    else:
        doc = fitz.open(pdf_bytes_or_path)
    try:
        return "".join(p.get_text() for p in doc)
    finally:
        doc.close()


def parse_po_text(full_text: str) -> dict:
    """Parse the extracted text of a Sun Automation PO.

    Returns ``{"po_number": str|None, "items": [LineItem-as-dict, ...]}``.
    """
    m = PONUM_RE.search(full_text)
    po_number = m.group(1) if m else None

    lines = [s.strip() for s in full_text.splitlines()]
    items: list[LineItem] = []
    i = 0
    while i < len(lines):
        # Anchor on the 5-row column header that precedes every line item.
        if (
            i + 4 < len(lines)
            and tuple(lines[i:i + 5]) == HEADER_ROWS
        ):
            # Skip 6 header rows (header_rows + "Ven Part")
            j = i + 6
            if j + 5 >= len(lines):
                break
            line_n_s = lines[j]
            uom = lines[j + 1]
            unit_m = PRICE_PER_RE.match(lines[j + 2])
            ext_m = NUMBER_RE.match(lines[j + 3])
            qty_m = NUMBER_RE.match(lines[j + 4])
            part_line = lines[j + 5]
            # Description may continue on following lines until the next
            # anchor (release requirement header, or next "Line" header).
            k = j + 6
            while k < len(lines) and lines[k] and lines[k] not in LINE_TERMINATORS:
                part_line += " " + lines[k]
                k += 1
            part_m = PART_LINE_RE.match(part_line)
            if line_n_s.isdigit() and unit_m and ext_m and qty_m and part_m:
                raw_part = part_m.group("part")
                items.append(
                    LineItem(
                        line=int(line_n_s),
                        part=raw_part,
                        part_digits=normalize_part(raw_part),
                        rev=part_m.group("rev"),
                        description=part_m.group("desc"),
                        qty=float(qty_m.group("n")),
                        unit_price=float(unit_m.group("unit")),
                        ext_price=float(ext_m.group("n")),
                        uom=uom,
                    )
                )
            i = k
            continue
        i += 1

    return {
        "po_number": po_number,
        "items": [asdict(it) for it in items],
    }


def parse_po(pdf_bytes_or_path) -> dict:
    """Convenience: text-extract + parse in one call."""
    return parse_po_text(extract_text(pdf_bytes_or_path))


def find_value_for_card(
    po_data: dict,
    *,
    line_n: int | None = None,
    part_digits: str | None = None,
) -> dict | None:
    """Return the matching line-item dict from a parsed PO, or None.

    Prefers line-number match (cards are named ``SUN PO {ponum} Line {n}``).
    Falls back to part-number match if line number doesn't resolve.
    """
    items: list[dict] = po_data.get("items") or []
    if line_n is not None:
        for it in items:
            if it["line"] == line_n:
                return it
    if part_digits:
        norm = normalize_part(part_digits)
        for it in items:
            if it["part_digits"] == norm:
                return it
    return None


def total(items: Iterable[dict]) -> float:
    return round(sum((it or {}).get("ext_price", 0.0) for it in items), 2)
