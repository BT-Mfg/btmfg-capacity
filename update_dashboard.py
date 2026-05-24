"""Build the value-dashboard data file.

For every active card on the Trello board:
1. Parse PO number + line number from the card name (``SUN PO {po} Line {n}``).
2. Fetch the latest Sun PO PDF (Gmail, with a local-folder cache and
   on-disk byte cache).
3. Parse the PDF, find the line item, and record its extended price.
4. Aggregate totals (grand, by list, by customer, overdue).
5. Write ``docs/dashboard.json`` and ``docs/last_updated.json``.
6. Git-commit and push so GitHub Pages picks up the change.

Run manually:  ``python3 update_dashboard.py``
Run on cron via the launchd plist in ``launchd/com.btmfg.dashboard.plist``.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from gmail_client import GmailClient
from po_source import POSource
from trello_client import TrelloClient
from value import normalize_part

load_dotenv()

HERE = Path(__file__).resolve().parent
DOCS = HERE / "docs"
DOCS.mkdir(exist_ok=True)

# Cards in these lists (case-insensitive) are considered "shipped/done" and
# excluded from the value totals.
EXCLUDE_LISTS = {
    s.strip().lower()
    for s in os.environ.get(
        "EXCLUDE_LISTS", "Shipped,Done,Complete,Archived,Archive"
    ).split(",")
    if s.strip()
}

# Custom field name hints (case-insensitive substring match) for the part
# number we set during intake.
PART_FIELD_HINTS = ["part", "part number", "part #"]

# Card-name pattern set by intake_po.py: "SUN PO 351934 Line 2"
CARD_NAME_RE = re.compile(
    r"\bSUN\s+PO\s+(?P<po>\d{5,7})\s+Line\s+(?P<line>\d+)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Customer detection from card name.
# Today every card is Sun Automation, but we already infrastructure it for
# the day Ben takes on another customer — the dashboard groups by customer.

def detect_customer(card_name: str) -> str:
    name = (card_name or "").upper()
    if "SUN" in name and "PO" in name:
        return "Sun Automation"
    return "Other"


# ---------------------------------------------------------------------------

def find_part_field_id(custom_fields: list[dict]) -> str | None:
    for field in custom_fields:
        n = (field.get("name") or "").lower()
        for hint in PART_FIELD_HINTS:
            if hint in n:
                return field["id"]
    return None


def card_part_digits(card: dict, part_field_id: str | None) -> str | None:
    if not part_field_id:
        return None
    for item in card.get("customFieldItems") or []:
        if item.get("idCustomField") != part_field_id:
            continue
        value = item.get("value") or {}
        raw = value.get("text") or value.get("number")
        if raw is not None:
            return normalize_part(str(raw))
    return None


def is_overdue(card: dict, now_utc: datetime) -> bool:
    due_s = card.get("due")
    if not due_s:
        return False
    try:
        # Trello sends RFC3339 with trailing Z
        due_dt = datetime.fromisoformat(due_s.replace("Z", "+00:00"))
    except ValueError:
        return False
    return due_dt < now_utc


def build_dashboard() -> dict:
    key = os.environ.get("TRELLO_API_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    if not key or not token:
        raise RuntimeError(
            "Missing TRELLO_API_KEY or TRELLO_TOKEN. Fill in .env."
        )
    board_id = os.environ.get("TRELLO_BOARD_ID", "YG0Dh7Kp")

    trello = TrelloClient(api_key=key, token=token)
    lists = trello.lists(board_id)
    cards = trello.cards(board_id)
    custom_fields = trello.custom_fields(board_id)
    part_field_id = find_part_field_id(custom_fields)

    list_by_id = {l["id"]: l for l in lists}
    excluded_list_ids = {
        l["id"]
        for l in lists
        if (l.get("name") or "").strip().lower() in EXCLUDE_LISTS
    }

    # Gmail is optional: if creds aren't set up yet, fall back to local folder only.
    try:
        gmail = GmailClient()
        # Touch the service so we surface auth issues now instead of mid-loop.
        gmail._service()  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Gmail unavailable ({exc}); using folder-only", flush=True)
        gmail = None

    local_dir = os.environ.get("LOCAL_PO_DIR") or None
    po_src = POSource(gmail_client=gmail, local_dir=local_dir)

    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for card in cards:
        if card["idList"] in excluded_list_ids:
            continue
        name = card.get("name") or ""
        m = CARD_NAME_RE.search(name)
        po_num = m.group("po") if m else None
        line_n = int(m.group("line")) if m else None
        part_digits = card_part_digits(card, part_field_id)

        row = {
            "card_id": card["id"],
            "name": name,
            "url": card.get("url"),
            "list_id": card["idList"],
            "list_name": (list_by_id.get(card["idList"]) or {}).get("name", "?"),
            "customer": detect_customer(name),
            "po_number": po_num,
            "line": line_n,
            "part": part_digits,
            "due": card.get("due"),
            "overdue": is_overdue(card, now),
            "value": None,
            "qty": None,
            "unit_price": None,
            "description": None,
            "status": "no_po_number_in_name" if not po_num else "pending",
            "source": None,
        }

        if po_num:
            try:
                parsed = po_src.get(po_num)
                # Prefer line# match; fall back to part# match.
                item = None
                if line_n is not None:
                    for it in parsed["items"]:
                        if it["line"] == line_n:
                            item = it
                            break
                if item is None and part_digits:
                    for it in parsed["items"]:
                        if it["part_digits"] == part_digits:
                            item = it
                            break
                if item is None:
                    row["status"] = "line_not_found_in_po"
                else:
                    row["value"] = item["ext_price"]
                    row["qty"] = item["qty"]
                    row["unit_price"] = item["unit_price"]
                    row["description"] = item["description"]
                    if not row["part"]:
                        row["part"] = item["part_digits"]
                    row["status"] = "ok"
                row["source"] = "gmail-or-folder"
            except FileNotFoundError:
                row["status"] = "no_po_found"
            except Exception as exc:  # noqa: BLE001
                row["status"] = f"error: {exc.__class__.__name__}"
                print(
                    f"[error] card {card['id']} ({name}): {exc}", flush=True
                )
        rows.append(row)

    # ---- Aggregates -------------------------------------------------------

    def sum_value(items):
        return round(sum(r["value"] or 0 for r in items), 2)

    grand = sum_value(rows)
    overdue_total = sum_value([r for r in rows if r.get("overdue")])

    by_list_map: dict[str, dict] = {}
    for r in rows:
        bucket = by_list_map.setdefault(
            r["list_id"],
            {
                "list_id": r["list_id"],
                "list_name": r["list_name"],
                "card_count": 0,
                "value": 0.0,
                "missing": 0,
            },
        )
        bucket["card_count"] += 1
        if r["value"] is not None:
            bucket["value"] += r["value"]
        else:
            bucket["missing"] += 1
    # Order by list position
    list_pos = {l["id"]: l.get("pos", 0) for l in lists}
    by_list = sorted(by_list_map.values(), key=lambda b: list_pos.get(b["list_id"], 0))
    for b in by_list:
        b["value"] = round(b["value"], 2)

    by_customer_map: dict[str, dict] = {}
    for r in rows:
        bucket = by_customer_map.setdefault(
            r["customer"],
            {"customer": r["customer"], "card_count": 0, "value": 0.0, "missing": 0},
        )
        bucket["card_count"] += 1
        if r["value"] is not None:
            bucket["value"] += r["value"]
        else:
            bucket["missing"] += 1
    by_customer = sorted(by_customer_map.values(), key=lambda b: -b["value"])
    for b in by_customer:
        b["value"] = round(b["value"], 2)

    missing_count = sum(1 for r in rows if r["value"] is None)

    return {
        "generated_at": now.isoformat(),
        "board_id": board_id,
        "grand_total": grand,
        "overdue_total": overdue_total,
        "missing_count": missing_count,
        "card_count": len(rows),
        "by_list": by_list,
        "by_customer": by_customer,
        "cards": sorted(rows, key=lambda r: -(r["value"] or 0)),
    }


def write_outputs(data: dict) -> None:
    payload = json.dumps(data, indent=2, default=str)
    (DOCS / "dashboard.json").write_text(payload)
    # Lightweight "freshness" file the page can poll cheaply.
    (DOCS / "last_updated.json").write_text(
        json.dumps({"generated_at": data["generated_at"]})
    )
    # Disable Jekyll so GitHub Pages serves files starting with `_` correctly
    # (and to skip a build step we don't need).
    (DOCS / ".nojekyll").write_text("")
    # Inject password hash so the dashboard's gate works. If unset, the
    # gate is bypassed (the page is then fully public — but only people
    # who know the GitHub Pages URL can find it).
    pw = os.environ.get("DASHBOARD_PASSWORD", "").strip()
    if pw:
        pw_hash = hashlib.sha256(pw.encode("utf-8")).hexdigest()
        (DOCS / "auth.js").write_text(f'window.PW_HASH="{pw_hash}";\n')
    else:
        (DOCS / "auth.js").write_text("window.PW_HASH='';\n")


def git_push() -> None:
    """Stage docs/, commit if changed, push to origin/main.

    Silently no-ops if there's no remote or no diff. Logs failures so cron
    runs surface them in launchd's log files.
    """

    def _run(*cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd, cwd=HERE, check=False, capture_output=True, text=True
        )

    if not (HERE / ".git").exists():
        print("[info] not a git repo yet — skipping push", flush=True)
        return
    if _run("git", "remote", "get-url", "origin").returncode != 0:
        print("[info] no 'origin' remote — skipping push", flush=True)
        return

    _run("git", "add", "docs/")
    diff = _run("git", "diff", "--cached", "--quiet")
    if diff.returncode == 0:
        print("[info] no dashboard changes to commit", flush=True)
        return
    msg = f"dashboard update {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    c = _run("git", "commit", "-m", msg)
    if c.returncode != 0:
        print(f"[warn] git commit failed: {c.stderr}", flush=True)
        return
    p = _run("git", "push", "origin", "main")
    if p.returncode != 0:
        print(f"[warn] git push failed: {p.stderr}", flush=True)
    else:
        print("[ok] pushed dashboard update", flush=True)


def main() -> int:
    try:
        data = build_dashboard()
        write_outputs(data)
        print(
            f"[ok] {data['card_count']} cards, "
            f"${data['grand_total']:,.2f} grand total, "
            f"{data['missing_count']} missing values",
            flush=True,
        )
        git_push()
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
