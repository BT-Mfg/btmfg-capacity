#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "======================================"
echo "  BT MFG — Gmail Authorization"
echo "======================================"
echo ""
echo "  A browser window will open asking you"
echo "  to sign in and authorize Gmail access."
echo ""
echo "  If you see 'This app isn't verified':"
echo "  → Click 'Advanced'"
echo "  → Click 'Go to BTMFG Dashboard (unsafe)'"
echo "  → Click 'Continue'"
echo ""
echo "  Starting..."
echo ""

.venv/bin/python -c "
from gmail_client import GmailClient
c = GmailClient()
c._service()
print('  ✓ Gmail authorized successfully!')
print('  token.json has been saved.')
"

echo ""
read -p "  Press Enter to close..."
