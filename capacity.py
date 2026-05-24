"""Per-column workload computation from Trello board state.

Pure functions over the JSON shape Trello returns — easy to unit-test, no IO.
Heuristics for finding the relevant custom fields are case-insensitive
substring matches so Ben can name them however he likes within reason.
"""
from __future__ import annotations

from typing import Any

# Case-insensitive substring hints for matching Trello custom field names.
# First match wins; order matters.
FIELD_HINTS: dict[str, list[str]] = {
    "setup": ["setup min", "setup minutes", "setup time", "setup"],
    "cycle": ["cycle min", "cycle minutes", "cycle time", "minutes per part", "cycle"],
    "qty":   ["qty", "quantity", "count"],
}


def find_field(custom_fields: list[dict], hints: list[str]) -> str | None:
    """Return the id of the first custom field whose name matches any hint."""
    for field in custom_fields:
        name = (field.get("name") or "").lower()
        for hint in hints:
            if hint in name:
                return field["id"]
    return None


def card_minutes(card: dict, field_ids: dict[str, str | None], default_min: float) -> float:
    """Estimated minutes to run this card: setup + cycle * qty.

    Missing setup → 0. Missing cycle → default_min. Missing qty → 1.
    """
    setup = 0.0
    cycle: float | None = None
    qty = 1.0
    for item in card.get("customFieldItems") or []:
        value = item.get("value") or {}
        raw = value.get("number", value.get("text"))
        try:
            num = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            num = None
        if num is None:
            continue
        fid = item.get("idCustomField")
        if fid == field_ids.get("setup"):
            setup = num
        elif fid == field_ids.get("cycle"):
            cycle = num
        elif fid == field_ids.get("qty"):
            qty = num
    if cycle is None:
        cycle = default_min
    return setup + cycle * qty


def status_for(hours: float, thresh_yellow: float, thresh_red: float) -> str:
    """Traffic-light bucket for a queued-hours value."""
    if hours == 0:
        return "empty"
    if hours < thresh_yellow:
        return "green"
    if hours < thresh_red:
        return "yellow"
    return "red"


def compute_capacity(
    trello: Any,
    board_id: str,
    *,
    default_min: float = 60,
    hours_per_day: float = 8,
    thresh_yellow: float = 32,
    thresh_red: float = 80,
) -> dict:
    """Fetch board state and return a summary dict ready for the template."""
    lists = trello.lists(board_id)
    cards = trello.cards(board_id)
    custom_fields = trello.custom_fields(board_id)

    field_ids = {
        kind: find_field(custom_fields, hints)
        for kind, hints in FIELD_HINTS.items()
    }
    has_real_data = bool(field_ids.get("setup") or field_ids.get("cycle"))

    # Initialize buckets for every open list, preserving position order.
    by_list: dict[str, dict] = {
        l["id"]: {
            "id": l["id"],
            "name": l["name"],
            "pos": l["pos"],
            "cards": [],
            "total_min": 0.0,
        }
        for l in lists
    }

    for card in cards:
        bucket = by_list.get(card["idList"])
        if bucket is None:
            continue
        minutes = card_minutes(card, field_ids, default_min)
        bucket["cards"].append(
            {
                "name": card["name"],
                "url": card["url"],
                "due": card.get("due"),
                "minutes": round(minutes, 1),
            }
        )
        bucket["total_min"] += minutes

    columns = []
    for entry in sorted(by_list.values(), key=lambda x: x["pos"]):
        hours = entry["total_min"] / 60.0
        columns.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "card_count": len(entry["cards"]),
                "total_hours": round(hours, 1),
                "days_at_capacity": (
                    round(hours / hours_per_day, 1) if hours_per_day > 0 else 0
                ),
                "status": status_for(hours, thresh_yellow, thresh_red),
                # Cards sorted with due-dated ones first, oldest first.
                "cards": sorted(
                    entry["cards"], key=lambda c: (c["due"] or "zzzz")
                ),
            }
        )

    return {
        "columns": columns,
        "has_real_field_data": has_real_data,
        "thresholds": {
            "yellow": thresh_yellow,
            "red": thresh_red,
            "hours_per_day": hours_per_day,
            "default_min": default_min,
        },
        "board_id": board_id,
        "field_detection": {
            kind: bool(fid) for kind, fid in field_ids.items()
        },
    }
