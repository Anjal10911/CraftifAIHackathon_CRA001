#!/usr/bin/env bash
set -e
echo "======================================================"
echo "   Blind-Spot Watchdog Demo (PipeGen Safety Add-on)"
echo "======================================================"
echo ""
echo "Running simulated demo feed (~22 seconds)..."
echo "Watches for simulated camera/pipeline failure and recovery."
echo ""

if command -v python3 &>/dev/null; then
    python3 watchdog.py --demo --timeout 2
elif command -v python &>/dev/null; then
    python watchdog.py --demo --timeout 2
else
    echo "Error: Python is not installed or not in PATH."
    exit 1
fi

echo ""
echo "======================================================"
echo " Demo completed! Incident log written to:"
echo " incident_log.jsonl"
echo ""
echo " Next steps:"
echo " 1. Open dashboard.html in your browser."
echo " 2. Click 'Load incident_log.jsonl' (or drag and drop it)."
echo "======================================================"
echo ""
