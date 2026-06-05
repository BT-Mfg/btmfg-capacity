#!/bin/bash
# One-time setup for this Mac.
# Double-click to run. A Terminal window will open automatically.

set -e
cd "$(dirname "$0")"

echo ""
echo "======================================"
echo "  BT MFG — Setup This Mac"
echo "======================================"
echo ""

# ---- 1. Homebrew check -------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
  echo "  ERROR: Homebrew is not installed."
  echo "  Install it first at https://brew.sh, then re-run this script."
  echo ""
  read -p "  Press Enter to exit..."
  exit 1
fi

# ---- 2. GitHub CLI -----------------------------------------------------------
if ! command -v gh >/dev/null 2>&1; then
  echo "  Installing GitHub CLI (gh)..."
  brew install gh
else
  echo "  ✓ gh already installed ($(gh --version | head -1))"
fi

# ---- 3. gh auth login --------------------------------------------------------
if ! gh auth status >/dev/null 2>&1; then
  echo ""
  echo "  You need to sign in to GitHub."
  echo "  Choose: GitHub.com → HTTPS → Login with a web browser"
  echo "  (A code will appear — paste it in the browser that opens)"
  echo ""
  gh auth login
else
  echo "  ✓ Already signed in to GitHub ($(gh auth status 2>&1 | grep 'Logged in' | head -1))"
fi

# ---- 4. Python venv ----------------------------------------------------------
if [ ! -d ".venv" ]; then
  echo ""
  echo "  Creating Python virtual environment..."
  python3 -m venv .venv
  echo "  Installing dependencies..."
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt -q
  echo "  ✓ Dependencies installed"
else
  echo "  ✓ .venv already exists — updating dependencies..."
  .venv/bin/pip install -r requirements.txt -q
fi

# ---- 5. Trello smoke test ----------------------------------------------------
echo ""
echo "  Testing Trello connection..."
.venv/bin/python -c "
from dotenv import load_dotenv; import os, sys
from trello_client import TrelloClient
load_dotenv()
key = os.environ.get('TRELLO_API_KEY','')
token = os.environ.get('TRELLO_TOKEN','')
if not key or not token:
    print('  ERROR: TRELLO_API_KEY or TRELLO_TOKEN missing from .env')
    sys.exit(1)
t = TrelloClient(key, token)
lists = t.lists(os.environ.get('TRELLO_BOARD_ID','YG0Dh7Kp'))
print('  ✓ Trello connected — board columns:')
for l in lists: print('      -', l['name'])
" || echo "  ✗ Trello test failed — check your .env credentials"

echo ""
echo "======================================"
echo "  Setup complete!"
echo ""
echo "  NEXT STEP: Set up Gmail OAuth."
echo "  Claude will walk you through that"
echo "  in the browser."
echo "======================================"
echo ""
read -p "  Press Enter to close..."
