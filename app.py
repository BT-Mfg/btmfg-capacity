"""BT MFG Capacity Dashboard — Flask app.

Reads the Trello board live, groups cards by column (= machine), and shows
queued hours / days at capacity per column. Run with `python3 app.py` or via
the `start.command` launcher.
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

from capacity import compute_capacity
from trello_client import TrelloClient

load_dotenv()

app = Flask(__name__)


def _trello() -> TrelloClient:
    key = os.environ.get("TRELLO_API_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    if not key or not token:
        raise RuntimeError(
            "Missing TRELLO_API_KEY or TRELLO_TOKEN. Copy .env.example to .env "
            "and fill in your credentials."
        )
    return TrelloClient(api_key=key, token=token)


@app.route("/")
def home():
    return render_template("capacity.html")


@app.route("/api/capacity")
def api_capacity():
    try:
        data = compute_capacity(
            _trello(),
            board_id=os.environ.get("TRELLO_BOARD_ID", "YG0Dh7Kp"),
            default_min=int(os.environ.get("DEFAULT_MIN_PER_CARD", 60)),
            hours_per_day=float(os.environ.get("HOURS_PER_DAY", 8)),
            thresh_yellow=float(os.environ.get("THRESH_YELLOW_HRS", 32)),
            thresh_red=float(os.environ.get("THRESH_RED_HRS", 80)),
        )
        return jsonify(data)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    app.run(host="127.0.0.1", port=port, debug=False)
