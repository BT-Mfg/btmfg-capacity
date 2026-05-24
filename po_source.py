"""Caching layer that fetches PO PDFs from Gmail (or a local folder fallback).

We hit Gmail at most once per PO number per run, and cache the bytes on
disk so subsequent runs (and re-runs after failures) don't re-download.
The cache lives at ``po_cache/{po}.pdf`` and is git-ignored.

If a local folder is configured (``LOCAL_PO_DIR`` env var) we look there
first — useful if you already keep POs synced to OneDrive — and only fall
back to Gmail for missing POs.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from value import parse_po

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "po_cache"


class POSource:
    def __init__(
        self,
        gmail_client=None,
        local_dir: Optional[Path | str] = None,
        cache_dir: Path | str = CACHE_DIR,
    ) -> None:
        self._gmail = gmail_client
        self._local = Path(local_dir).expanduser() if local_dir else None
        self._cache = Path(cache_dir)
        self._cache.mkdir(exist_ok=True)
        self._memo: dict[str, dict] = {}

    def get(self, po_number: str | int) -> dict:
        """Return parsed-PO dict for the given PO number.

        On miss, raises FileNotFoundError so callers can mark the card as
        ``no_po_found``.
        """
        po = str(po_number)
        if po in self._memo:
            return self._memo[po]
        pdf_bytes = self._load_bytes(po)
        if pdf_bytes is None:
            raise FileNotFoundError(f"No PO PDF found for {po}")
        parsed = parse_po(pdf_bytes)
        self._memo[po] = parsed
        return parsed

    # ---- internals ---------------------------------------------------------

    def _load_bytes(self, po: str) -> Optional[bytes]:
        # 1) Cache
        cached = self._cache / f"{po}.pdf"
        if cached.exists():
            return cached.read_bytes()
        # 2) Local folder
        if self._local and self._local.is_dir():
            for path in self._local.iterdir():
                if not path.is_file():
                    continue
                if po in path.name and path.suffix.lower() == ".pdf":
                    data = path.read_bytes()
                    cached.write_bytes(data)
                    return data
        # 3) Gmail
        if self._gmail is not None:
            data = self._gmail.latest_po_pdf(po)
            if data is not None:
                cached.write_bytes(data)
                return data
        return None
