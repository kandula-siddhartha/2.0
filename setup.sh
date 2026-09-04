#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "  PASSIVE SHELTER THERMAL PLATFORM - INSTALLER"
echo "  PyAnsys MAPDL Transient Simulation Engine"
echo "======================================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

python3 setup_platform.py "$@"
