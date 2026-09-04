"""
Passive Shelter Thermal Platform — Root Master Launcher
Starts the unified server (FastAPI backend + React SPA frontend on port 8000)
and launches the browser automatically.
"""
from __future__ import annotations

import sys
import os
import webbrowser
import threading
import time
from pathlib import Path

# Verify dependencies before starting
try:
    import fastapi
    import uvicorn
    import sqlalchemy
except ImportError:
    print("\n[!] Core dependencies appear to be missing.")
    print("    Running automated setup program first (setup_platform.py)...")
    setup_script = Path(__file__).parent / "setup_platform.py"
    if setup_script.exists():
        import subprocess
        subprocess.check_call([sys.executable, str(setup_script)])
    else:
        print("Please run 'setup.bat' or 'python setup_platform.py' first.")
        sys.exit(1)

target_dir = Path(__file__).parent / "passive-shelter-thermal-platform"
os.chdir(str(target_dir))
sys.path.insert(0, str(target_dir))


def _open_browser():
    time.sleep(1.8)
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    from run import main
    main()
