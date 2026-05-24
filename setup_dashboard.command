#!/bin/bash
# One-time setup for the BT MFG value dashboard:
#  1. Ensure the venv exists and dependencies are installed.
#  2. Render the launchd plist from its template with this folder's path.
#  3. Load (or reload) the launchd job so update_dashboard.py runs every 15 min.
#  4. Run update_dashboard.py once now so docs/ is populated immediately.
#
# Safe to re-run any time (e.g. after editing the template or moving the folder).

set -e
cd "$(dirname "$0")"
REPO_DIR="$(pwd)"
VENV="$REPO_DIR/.venv"
PY="$VENV/bin/python"

echo
echo "  BT MFG — Dashboard Setup"
echo "  ========================="
echo "  Repo: $REPO_DIR"
echo

# 1) venv
if [ ! -d "$VENV" ]; then
  echo "  [1/4] Creating Python venv + installing dependencies..."
  python3 -m venv "$VENV"
fi
"$PY" -m pip install --upgrade pip --quiet
"$PY" -m pip install -r requirements.txt --quiet
echo "  [1/4] venv ready."

# 2) .env sanity
if [ ! -f .env ]; then
  cp .env.example .env
  echo
  echo "  [!] No .env yet — created one for you. Fill in TRELLO_API_KEY,"
  echo "      TRELLO_TOKEN, and (optionally) DASHBOARD_PASSWORD, then re-run."
  echo
  open .env
  exit 1
fi
echo "  [2/4] .env present."

# 3) Render + load the launchd plist
PLIST_LOCAL="$REPO_DIR/launchd/com.btmfg.dashboard.plist"
PLIST_LOADED="$HOME/Library/LaunchAgents/com.btmfg.dashboard.plist"

mkdir -p "$REPO_DIR/launchd"
sed "s|__REPO_DIR__|$REPO_DIR|g" \
  "$REPO_DIR/launchd/com.btmfg.dashboard.plist.template" > "$PLIST_LOCAL"
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_LOCAL" "$PLIST_LOADED"

# launchctl bootstrap is the modern replacement for load/unload.
launchctl bootout "gui/$(id -u)/com.btmfg.dashboard" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_LOADED"
echo "  [3/4] launchd job loaded (runs every 15 min)."

# 4) Kick a run immediately
echo "  [4/4] Running update_dashboard.py once now..."
"$PY" update_dashboard.py || echo "  (first run had errors — see output above)"

echo
echo "  Done. To check status:"
echo "    launchctl print gui/\$(id -u)/com.btmfg.dashboard | head -40"
echo "  Logs:"
echo "    tail -f launchd/out.log launchd/err.log"
echo
