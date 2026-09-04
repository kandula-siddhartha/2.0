#!/usr/bin/env python3
"""
Passive Shelter Thermal Platform — Automated Setup Program
Cross-platform environment configuration, dependency installer, and system diagnostics.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = ROOT_DIR / "passive-shelter-thermal-platform"
BACKEND_DIR = PROJECT_DIR / "backend"
FRONTEND_DIR = PROJECT_DIR / "frontend"
REQUIREMENTS_FILE = BACKEND_DIR / "requirements.txt"
STATIC_DIR = BACKEND_DIR / "static"


def print_banner(text: str) -> None:
    line = "=" * 72
    print(f"\n{line}")
    print(f"  {text}")
    print(f"{line}\n")


def print_step(step_num: int, title: str) -> None:
    print(f"\n[Step {step_num}] {title}")
    print("-" * 50)


def check_python_version() -> bool:
    print(f"Python executable: {sys.executable}")
    print(f"Python version:    {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print(" [ERROR] Python 3.10 or newer is required to run this platform.")
        return False
    print(" [OK] Python version compatible.")
    return True


def install_python_dependencies(check_only: bool = False) -> bool:
    if not REQUIREMENTS_FILE.exists():
        print(f" [ERROR] Requirements file not found at: {REQUIREMENTS_FILE}")
        return False

    if check_only:
        print(" Skipping pip install (--check-only flag active).")
        return True

    print(f"Installing Python packages from {REQUIREMENTS_FILE.name}...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            cwd=str(ROOT_DIR),
        )
        print(" [OK] Python dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f" [ERROR] Failed to install Python dependencies: {e}")
        return False


def verify_python_packages() -> bool:
    core_packages = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI server"),
        ("sqlalchemy", "Database ORM"),
        ("pydantic", "Data validation"),
        ("numpy", "Numerical computing"),
        ("scipy", "Scientific calculations"),
        ("ansys.mapdl.core", "PyMAPDL ANSYS interface"),
        ("gmsh", "Gmsh 3D CAD/mesh kernel"),
        ("reportlab", "PDF report generator"),
    ]

    print("Verifying core Python packages:")
    all_ok = True
    for pkg, desc in core_packages:
        try:
            __import__(pkg)
            print(f"  * {pkg:<20} [OK] ({desc})")
        except ImportError:
            print(f"  * {pkg:<20} [MISSING] ({desc})")
            all_ok = False

    return all_ok


def setup_frontend(check_only: bool = False) -> bool:
    # 1. Check if Node / npm is installed
    has_node = False
    try:
        res = subprocess.run(["node", "--version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            has_node = True
            node_ver = res.stdout.strip()
            print(f" Node.js detected: {node_ver}")
    except FileNotFoundError:
        pass

    has_npm = False
    try:
        res = subprocess.run(["npm", "--version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            has_npm = True
            npm_ver = res.stdout.strip()
            print(f" npm detected:     v{npm_ver}")
    except FileNotFoundError:
        pass

    # Check for existing prebuilt static assets
    has_prebuilt = (STATIC_DIR / "index.html").exists()

    if check_only:
        if has_prebuilt:
            print(" [OK] Prebuilt frontend distribution is ready in backend/static/.")
        else:
            print(" [NOTICE] Frontend has not been built yet.")
        return True

    if has_node and has_npm and FRONTEND_DIR.exists():
        print("\n Building production React SPA with Vite...")
        try:
            # Install frontend dependencies
            print("  Running npm install in frontend/...")
            subprocess.check_call(["npm", "install"], cwd=str(FRONTEND_DIR), shell=(os.name == "nt"))
            # Build
            print("  Running npm run build in frontend/...")
            subprocess.check_call(["npm", "run", "build"], cwd=str(FRONTEND_DIR), shell=(os.name == "nt"))

            dist_dir = FRONTEND_DIR / "dist"
            if dist_dir.exists():
                print(f"  Syncing build artifacts into {STATIC_DIR.relative_to(ROOT_DIR)}...")
                STATIC_DIR.mkdir(parents=True, exist_ok=True)
                for item in dist_dir.iterdir():
                    dst = STATIC_DIR / item.name
                    if item.is_dir():
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(item, dst)
                    else:
                        shutil.copy2(item, dst)
                print(" [OK] Frontend built and synced successfully.")
                return True
        except Exception as e:
            print(f" [WARNING] Frontend build failed: {e}")
            if has_prebuilt:
                print(" Falling back to existing prebuilt frontend assets.")
                return True
            return False
    else:
        if has_prebuilt:
            print(" Node.js/npm not found on system PATH.")
            print(" [OK] Using prebuilt production frontend in backend/static/.")
            print(" (Web UI will run fully functional without Node.js!)")
            return True
        else:
            print(" [WARNING] Node.js is required to build the frontend initially.")
            return False


def verify_ansys_environment() -> None:
    print("Checking ANSYS MAPDL installation status:")
    found_ansys = False

    # Check PyMAPDL detection
    try:
        from ansys.mapdl.core import launcher
        version = launcher.get_ansys_version()
        if version:
            print(f"  [OK] ANSYS detected via PyMAPDL: Version {version}")
            found_ansys = True
    except Exception:
        pass

    # Check environment variables
    if not found_ansys:
        for var in sorted(os.environ.keys()):
            if var.startswith("AWP_ROOT"):
                ansys_path = os.environ[var]
                print(f"  [OK] ANSYS environment variable found: {var} -> {ansys_path}")
                found_ansys = True

    # Common Windows paths
    if not found_ansys and os.name == "nt":
        for v in ["261", "251", "242", "241", "232"]:
            p = Path(f"C:/Program Files/ANSYS Inc/v{v}/ansys/bin/winx64/ansys{v}.exe")
            if p.exists():
                print(f"  [OK] Found ANSYS executable: {p}")
                found_ansys = True
                break

    if not found_ansys:
        print("  [INFO] ANSYS MAPDL was not auto-detected on standard PATHs.")
        print("         * If you have ANSYS installed, configure the executable path in the Web UI:")
        print("           (Settings -> ANSYS MAPDL Configuration).")
        print("         * Free ANSYS Student edition can be downloaded at:")
        print("           https://www.ansys.com/academic/students")
    else:
        print("  [READY] ANSYS MAPDL is configured for thermal FEA solving.")


def initialize_database() -> bool:
    print("Initializing SQLite database with materials and shelter models...")
    init_script = BACKEND_DIR / "app" / "database" / "init_db.py"
    if not init_script.exists():
        print(f" [ERROR] Database initialization script not found at: {init_script}")
        return False

    try:
        subprocess.check_call([sys.executable, str(init_script)], cwd=str(PROJECT_DIR))
        print(" [OK] Database initialized and seeded with materials library.")
        return True
    except subprocess.CalledProcessError as e:
        print(f" [ERROR] Database initialization failed: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated setup for Passive Shelter Thermal Platform.")
    parser.add_argument("--check-only", action="store_true", help="Perform checks only without modifying system.")
    parser.add_argument("--no-frontend", action="store_true", help="Skip frontend build step.")
    args = parser.parse_args()

    print_banner("PASSIVE SHELTER THERMAL PLATFORM — SETUP PROGRAM")
    print("Automated configuration for kandula-siddhartha/2.0")

    # Step 1: Python version
    print_step(1, "Python Environment Check")
    if not check_python_version():
        return 1

    # Step 2: Install Python dependencies
    print_step(2, "Python Dependencies Installation")
    if not install_python_dependencies(check_only=args.check_only):
        return 1

    # Step 3: Verify packages
    print_step(3, "Package Verification")
    if not verify_python_packages():
        print(" [WARNING] Some dependencies could not be imported. Review warnings above.")

    # Step 4: Frontend setup
    if not args.no_frontend:
        print_step(4, "Web Frontend Setup")
        setup_frontend(check_only=args.check_only)

    # Step 5: ANSYS Environment
    print_step(5, "ANSYS MAPDL Solver Diagnostics")
    verify_ansys_environment()

    # Step 6: Database initialization
    print_step(6, "Thermal Database Initialization")
    if not args.check_only:
        initialize_database()

    # Completion
    print_banner("SETUP COMPLETE — SYSTEM IS READY!")
    print("To launch the platform:")
    print("  * Windows:     Double-click start.bat   OR   python run.py")
    print("  * Linux/macOS: ./start.bat              OR   python run.py")
    print("\nWeb Platform URL: http://localhost:8000")
    print("API Documentation: http://localhost:8000/api/docs\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
