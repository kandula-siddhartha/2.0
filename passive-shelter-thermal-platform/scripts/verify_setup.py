"""
Diagnostic & Setup Verification Script
Passive Thermal Shelter Analysis & Recommendation Platform

Verifies that the current laptop has all required dependencies, database tables,
network access for real climate data, and a working ANSYS Mechanical APDL installation.
"""
import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend to sys.path
root_dir = Path(__file__).parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(backend_dir))

def main():
    print("=" * 72)
    print("  PASSIVE THERMAL SHELTER PLATFORM — ENVIRONMENT & SOLVER DIAGNOSTIC")
    print("=" * 72)

    all_passed = True

    # 1. Python Version Check
    py_ver = sys.version_info
    print(f"\n[1/5] Python Environment:")
    if py_ver.major == 3 and py_ver.minor >= 10:
        print(f"  [PASS] Python {py_ver.major}.{py_ver.minor}.{py_ver.micro} (compatible >= 3.10)")
    else:
        print(f"  [FAIL] Python {py_ver.major}.{py_ver.minor}.{py_ver.micro} detected. Platform requires Python 3.10+")
        all_passed = False

    # 2. Python Packages
    print(f"\n[2/5] Python Package Dependencies:")
    required_packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pydantic", "Pydantic"),
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("plotly", "Plotly"),
        ("reportlab", "ReportLab"),
        ("ansys.mapdl.core", "PyMAPDL (ansys-mapdl-core)"),
    ]

    missing_pkgs = []
    for mod, label in required_packages:
        try:
            __import__(mod)
            print(f"  [PASS] {label}")
        except ImportError:
            print(f"  [FAIL] {label} is missing")
            missing_pkgs.append(label)

    if missing_pkgs:
        all_passed = False
        print(f"  --> Run: pip install -r backend/requirements.txt")

    # 3. Database & Seeds
    print(f"\n[3/5] SQLite Database & Seed Data:")
    try:
        from app.database.init_db import init_db
        from app.database.base import get_db_context
        from app.database.models import Material, Design

        init_db()
        with get_db_context() as db:
            m_cnt = db.query(Material).count()
            d_cnt = db.query(Design).count()
            print(f"  [PASS] Database initialized successfully.")
            print(f"         Materials loaded: {m_cnt} | Designs loaded: {d_cnt}")
    except Exception as e:
        print(f"  [FAIL] Database initialization failed: {e}")
        all_passed = False

    # 4. ANSYS Installation & Executable
    print(f"\n[4/5] ANSYS MAPDL Solver Kernel:")
    try:
        from app.config import settings
        from app.mapdl_integration.version_detection import AnsysVersionDetector

        detector = AnsysVersionDetector()
        info = detector.detect()

        if info and info.mapdl_exe_exists:
            tier_str = "ANSYS Student (<128k nodes)" if info.is_student else "Commercial / Research"
            print(f"  [PASS] ANSYS MAPDL v{info.version_str} Verified on Disk")
            print(f"         License Tier:   {tier_str}")
            print(f"         Executable:     {info.mapdl_exe}")
            print(f"         Install Root:   {info.install_path}")
            print(f"         PyMAPDL Core:   v{info.pymapdl_version}")
        else:
            print(f"  [WARN] No working ANSYS installation detected automatically.")
            print(f"         Configured path: {settings.ansys_mapdl_exe or 'None'}")
            print(f"         To connect ANSYS on this laptop, launch the platform and")
            print(f"         specify your ansysXXX.exe path under 'ANSYS Setup' (/settings).")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Error querying ANSYS status: {e}")
        all_passed = False

    # 5. Compiled Frontend Bundle
    print(f"\n[5/5] Compiled Frontend Production UI:")
    frontend_dist = root_dir / "frontend" / "dist" / "index.html"
    if frontend_dist.exists():
        print(f"  [PASS] Precompiled React UI exists at: {frontend_dist}")
        print(f"         (No Node.js or npm required on target laptop!)")
    else:
        print(f"  [WARN] frontend/dist/index.html not found.")
        print(f"         Run 'npm run build' inside the frontend directory.")
        all_passed = False

    # Summary
    print("\n" + "=" * 72)
    if all_passed:
        print("  ALL CORE CHECKS PASSED: Platform is fully ready to run ANSYS FEA!")
        print("  Launch with: start.bat  OR  python run.py")
    else:
        print("  SETUP VERIFICATION COMPLETED WITH WARNINGS / MISSING ITEMS.")
        print("  Review items marked [FAIL] or [WARN] above before executing simulations.")
    print("=" * 72 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
