#!/bin/bash
cd "$(dirname "$0")"
SRC=$(ls ~/Downloads/client_secret_*.json 2>/dev/null | head -1)
if [ -z "$SRC" ]; then
  echo "ERROR: No client_secret_*.json found in Downloads."
  read -p "Press Enter to exit..."
  exit 1
fi
cp "$SRC" gmail_credentials.json
echo "✓ Moved: $(basename "$SRC") → gmail_credentials.json"
rm "$SRC"
echo "✓ Deleted original from Downloads"
echo ""
echo "Done! You can close this window."
read -p "Press Enter to exit..."
