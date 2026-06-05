"""Minimal Trello REST API wrapper for the capacity dashboard.

Only implements the three endpoints we need (lists, cards, custom fields).
Keep this small — if the toolkit grows, expand here or replace with `trello`
or `py-trello` from PyPI.
"""
from __future__ import annotations

from typing import Any

import requests

TRELLO_BASE = "https://api.trello.com/1"


class TrelloClient:
    def __init__(self, api_key: str, token: str, timeout: int = 20) -> None:
        self._auth = {"key": api_key, "token": token}
        self._timeout = timeout

    def _get(self, path: str, **params: Any) -> Any:
        resp = requests.get(
            f"{TRELLO_BASE}{path}",
            params={**self._auth, **params},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def lists(self, board_id: str) -> list[dict]:
        # fetch ALL lists (including closed/hidden) so we can resolve names for
        # any card, then let the caller decide what to exclude by list name.
        return self._get(
            f"/boards/{board_id}/lists",
            filter="all",
            fields="name,pos,closed",
        )

    def cards(self, board_id: str) -> list[dict]:
        return self._get(
            f"/boards/{board_id}/cards",
            customFieldItems="true",
            filter="open",
            fields="name,desc,due,idList,closed,url",
        )

    def custom_fields(self, board_id: str) -> list[dict]:
        return self._get(f"/boards/{board_id}/customFields")
