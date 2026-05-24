#!/bin/bash
# Double-click launcher for the BT MFG Capacity Dashboard.
# Creates a venv on first run, installs deps, starts the Flask server,
# opens the browser, and tails the server log until Ctrl+C.

set -e
cd "$(dirname "$0")"

VENV_DIR=".venv"
PY="$VENV_DIR/bin/python"

if [ ! -d "$VENV_DIR" ]; then
  echo ""
  echo "  First-run setup: creating Python venv and installing dependencies..."
  echo ""
  python3 -m venv "$VENV_DIR"
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r requirements.txt
fi

if [ ! -f ".env" ]; then
  echo ""
  echo "  WARNING: .env file is missing."
  echo "  Copy .env.example to .env and fill in your Trello credentials."
  echo ""
  cp .env.example .env
  echo "  Created a blank .env for you. Edit it now, then re-run this command."
  echo ""
  open .env
  exit 1
fi

# Read PORT from .env so the open URL matches.
PORT=$(grep -E '^PORT=' .env | tail -1 | cut -d'=' -f2)
PORT=${PORT:-8765}

echo ""
echo "  BT MFG — Capacity Dashboard"
echo "  ============================"
echo "  URL: http://localhost:${PORT}/"
echo "  Press Ctrl+C to stop."
echo ""

(sleep 1 && open "http://localhost:${PORT}/") &
exec "$PY" app.py
