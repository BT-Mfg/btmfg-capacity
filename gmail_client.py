"""Thin Gmail API wrapper for the value dashboard.

Reads PO PDFs from Gmail using OAuth. First-run pops a browser window for
consent; the resulting refresh token is cached at ``token.json`` next to
this file so subsequent runs are non-interactive.

Setup (one-time):

1. Create a Google Cloud project at https://console.cloud.google.com/.
2. Enable the **Gmail API** for the project.
3. Configure the OAuth consent screen (External, "Testing" mode is fine,
   add yourself as a test user).
4. Create OAuth client credentials of type **Desktop app**. Download the
   JSON and save it next to this file as ``gmail_credentials.json``.
5. First run of ``update_dashboard.py`` will open a browser for consent and
   write ``token.json``. Both files are in ``.gitignore``.

The token is bound to your account; refreshing happens transparently.
"""
from __future__ import annotations

import base64
import os
import re
from pathlib import Path
from typing import Optional

# google-api-python-client + google-auth-oauthlib are heavy enough that we
# only import them when actually instantiating GmailClient — keeps unit
# tests of value.py fast.

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
HERE = Path(__file__).resolve().parent
DEFAULT_CREDS = HERE / "gmail_credentials.json"
DEFAULT_TOKEN = HERE / "token.json"


def _build_service(creds_path: Path, token_path: Path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise RuntimeError(
                    f"Missing OAuth client file at {creds_path}. "
                    "See gmail_client.py docstring for one-time setup."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


class GmailClient:
    """Search Gmail and download PDF attachments by PO number."""

    def __init__(
        self,
        creds_path: Path | str = DEFAULT_CREDS,
        token_path: Path | str = DEFAULT_TOKEN,
        sender_domain: str = "sunautomation.com",
    ) -> None:
        self._creds_path = Path(creds_path)
        self._token_path = Path(token_path)
        self._sender_domain = sender_domain
        self._svc = None  # built lazily on first use

    def _service(self):
        if self._svc is None:
            self._svc = _build_service(self._creds_path, self._token_path)
        return self._svc

    def search_messages(self, query: str, max_results: int = 10) -> list[dict]:
        """Return Gmail message stubs (id + threadId) matching ``query``."""
        resp = (
            self._service()
            .users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        return resp.get("messages") or []

    def get_message(self, message_id: str) -> dict:
        return (
            self._service()
            .users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

    def get_attachment_bytes(self, message_id: str, attachment_id: str) -> bytes:
        att = (
            self._service()
            .users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        data = att.get("data", "")
        # Gmail uses URL-safe base64
        return base64.urlsafe_b64decode(data.encode("ascii"))

    # ---- High-level helper -------------------------------------------------

    def latest_po_pdf(self, po_number: str | int) -> Optional[bytes]:
        """Return the bytes of the newest PDF matching this PO, or None.

        We search for the PO number in the subject/body of messages from
        the configured sender domain, scan results newest-first (Gmail's
        default), and return the first PDF attachment whose filename
        contains the PO number.
        """
        po = str(po_number)
        # Gmail search: limit to sender domain, must have attachment, must
        # mention the PO number anywhere in the message.
        query = f"from:{self._sender_domain} has:attachment {po}"
        msgs = self.search_messages(query, max_results=20)
        for stub in msgs:
            msg = self.get_message(stub["id"])
            for part in _iter_parts(msg.get("payload") or {}):
                filename = part.get("filename") or ""
                if not filename.lower().endswith(".pdf"):
                    continue
                # Filenames look like "Sun Automation_PO_353554.pdf" — match
                # the PO number anywhere in the filename.
                if po not in filename:
                    continue
                body = part.get("body") or {}
                att_id = body.get("attachmentId")
                if not att_id:
                    continue
                try:
                    return self.get_attachment_bytes(stub["id"], att_id)
                except Exception:
                    continue
        return None


def _iter_parts(payload: dict):
    """Yield every leaf MIME part in a Gmail message payload."""
    if not payload:
        return
    parts = payload.get("parts")
    if parts:
        for p in parts:
            yield from _iter_parts(p)
    else:
        yield payload
