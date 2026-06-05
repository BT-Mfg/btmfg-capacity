#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo "======================================"
echo "  BT MFG — Test Dashboard Update"
echo "======================================"
echo ""
.venv/bin/python update_dashboard.py
echo ""
read -p "  Press Enter to close..."
