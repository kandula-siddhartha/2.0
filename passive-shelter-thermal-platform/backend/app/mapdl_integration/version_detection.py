"""
ANSYS installation detection and version checking.
Detects installed ANSYS products across environment variables, common disk locations,
and PyMAPDL discovery, verifying executable health and licensing limits.
"""
from __future__ import annotations

import os
import re
import sys
import glob
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class AnsysInstallInfo:
    version_int: int           # e.g. 261, 242, 232
    version_str: str           # e.g. "26.1", "24.2"
    install_path: str          # e.g. C:\Program Files\ANSYS Inc\v242
    mapdl_exe: str             # Full path to ansysXXX.exe
    mapdl_exe_exists: bool
    pymapdl_version: Optional[str]
    is_student: bool
    node_limit: Optional[int]  # ANSYS Student: ~128,000


class AnsysVersionDetector:
    """
    Detects ANSYS MAPDL installations dynamically across PyMAPDL, environment variables,
    and standard Windows drive installation paths.
    """

    STUDENT_NODE_LIMIT = 128000

    def _get_pymapdl_version(self) -> Optional[str]:
        try:
            import ansys.mapdl.core as pymapdl
            return pymapdl.__version__
        except Exception:
            return None

    def inspect_path(self, candidate_path: str) -> Optional[AnsysInstallInfo]:
        """
        Inspect a user-provided path (either to ansysXXX.exe or an installation directory)
        and extract valid AnsysInstallInfo.
        """
        if not candidate_path or not candidate_path.strip():
            return None

        p = Path(candidate_path.strip().strip('"').strip("'"))
        if not p.exists():
            return None

        mapdl_exe = ""
        install_root = ""

        # Case 1: Direct path to an executable
        if p.is_file() and p.name.lower().startswith("ansys") and p.suffix.lower() == ".exe":
            mapdl_exe = str(p.resolve())
            # Usually: <root>/ansys/bin/winx64/ansysXXX.exe -> root is 3 levels up
            try:
                install_root = str(p.parent.parent.parent.resolve())
            except Exception:
                install_root = str(p.parent.resolve())

        # Case 2: Path to directory
        elif p.is_dir():
            # Check if it has ansys/bin/winx64/ansys*.exe
            bin_dir = p / "ansys" / "bin" / "winx64"
            if bin_dir.exists():
                exes = sorted(bin_dir.glob("ansys*.exe"), key=lambda x: (len(x.name), x.name), reverse=True)
                if exes:
                    mapdl_exe = str(exes[0].resolve())
                    install_root = str(p.resolve())
            else:
                # Maybe path IS the bin dir
                exes = sorted(p.glob("ansys*.exe"), key=lambda x: (len(x.name), x.name), reverse=True)
                if exes:
                    mapdl_exe = str(exes[0].resolve())
                    try:
                        install_root = str(p.parent.parent.parent.resolve())
                    except Exception:
                        install_root = str(p.resolve())

        if not mapdl_exe or not Path(mapdl_exe).exists():
            return None

        # Parse version from executable name (e.g. ansys261.exe -> 261)
        m = re.search(r"ansys(\d{3})\.exe", Path(mapdl_exe).name, re.IGNORECASE)
        if not m:
            # Try to parse from path string (e.g. \v261\ or \v242\)
            m = re.search(r"[\\/]v(\d{3})[\\/]", mapdl_exe, re.IGNORECASE)

        if m:
            version_int = int(m.group(1))
            version_str = f"{version_int // 10}.{version_int % 10}"
        else:
            version_int = 242
            version_str = "24.2"

            version_int = 242
            version_str = "24.2"

        is_student = "student" in install_root.lower() or "student" in mapdl_exe.lower()

        return AnsysInstallInfo(
            version_int=version_int,
            version_str=version_str,
            install_path=install_root,
            mapdl_exe=mapdl_exe,
            mapdl_exe_exists=True,
            pymapdl_version=self._get_pymapdl_version(),
            is_student=is_student,
            node_limit=self.STUDENT_NODE_LIMIT if is_student else None,
        )

    def detect(self, explicit_path: Optional[str] = None) -> Optional[AnsysInstallInfo]:
        """
        Detect ANSYS installation.
        1. If explicit_path is given and valid, uses it.
        2. Otherwise checks PyMAPDL's get_available_ansys_installations().
        3. Otherwise scans AWP_ROOT environment variables.
        4. Otherwise scans standard Windows disk locations.
        """
        # 1. Explicit path check
        if explicit_path:
            info = self.inspect_path(explicit_path)
            if info:
                return info

        # 2. PyMAPDL discovery
        try:
            from ansys.mapdl.core import get_available_ansys_installations, get_mapdl_path
            installations = get_available_ansys_installations()
            if installations:
                version_int = abs(sorted(installations.keys())[0])
                install_path = installations[sorted(installations.keys())[0]]
                mapdl_exe = get_mapdl_path(allow_input=False)
                if mapdl_exe and Path(mapdl_exe).exists():
                    is_student = "Student" in install_path or "student" in str(mapdl_exe).lower()
                    return AnsysInstallInfo(
                        version_int=version_int,
                        version_str=f"{version_int // 10}.{version_int % 10}",
                        install_path=install_path,
                        mapdl_exe=mapdl_exe,
                        mapdl_exe_exists=True,
                        pymapdl_version=self._get_pymapdl_version(),
                        is_student=is_student,
                        node_limit=self.STUDENT_NODE_LIMIT if is_student else None,
                    )
        except Exception:
            pass

        # 3. Scan AWP_ROOT environment variables (e.g. AWP_ROOT261, AWP_ROOT252, AWP_ROOT242, AWP_ROOT232)
        awp_vars = [k for k in os.environ if k.upper().startswith("AWP_ROOT")]
        # Sort descending so newer versions are preferred
        awp_vars.sort(reverse=True)
        for var in awp_vars:
            val = os.environ.get(var)
            if val:
                info = self.inspect_path(val)
                if info:
                    return info

        # 4. Scan common disk locations on C:, D:, E:
        candidate_patterns = [
            r"C:\Program Files\ANSYS Inc\v*",
            r"C:\Program Files\ANSYS Inc\ANSYS Student\v*",
            r"D:\ANSYS\ANSYS Inc\v*",
            r"D:\ANSYS\ANSYS Inc\ANSYS Student\v*",
            r"D:\Program Files\ANSYS Inc\v*",
            r"C:\ANSYS\v*",
            r"C:\ANSYS Inc\v*",
        ]

        found_dirs = []
        for pattern in candidate_patterns:
            try:
                matches = glob.glob(pattern)
                found_dirs.extend(matches)
            except Exception:
                pass

        # Sort descending so highest version comes first
        found_dirs.sort(reverse=True)
        for cand_dir in found_dirs:
            info = self.inspect_path(cand_dir)
            if info:
                return info

        return None

    def get_supported_versions(self) -> list:
        """Return list of ANSYS versions supported by the installed PyMAPDL."""
        try:
            from ansys.mapdl.core import SUPPORTED_ANSYS_VERSIONS
            return list(SUPPORTED_ANSYS_VERSIONS.values())
        except Exception:
            return []
