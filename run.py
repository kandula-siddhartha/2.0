"""
Root launcher redirect to passive-shelter-thermal-platform/run.py
"""
import sys
import os
from pathlib import Path

target_dir = Path(__file__).parent / "passive-shelter-thermal-platform"
os.chdir(str(target_dir))
sys.path.insert(0, str(target_dir))

if __name__ == "__main__":
    from run import main
    main()
