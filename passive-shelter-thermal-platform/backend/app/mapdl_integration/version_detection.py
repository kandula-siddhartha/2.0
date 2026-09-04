"""
ANSYS installation detection and version checking.
Detects installed ANSYS products and verifies PyMAPDL compatibility.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AnsysInstallInfo:
    version_int: int           # e.g. 261
    version_str: str           # e.g. "26.1"
    install_path: str          # e.g. D:\ANSYS\...
    mapdl_exe: str             # Full path to ansysXXX.exe
    mapdl_exe_exists: bool
    pymapdl_version: Optional[str]
    is_student: bool
    node_limit: Optional[int]  # ANSYS Student: ~128,000


class AnsysVersionDetector:
    """
    Detects ANSYS MAPDL installations using PyMAPDL's built-in discovery.
    """

    STUDENT_NODE_LIMIT = 128000

    def detect(self) -> Optional[AnsysInstallInfo]:
        """
        Detect the ANSYS installation using PyMAPDL.
        Returns AnsysInstallInfo or None if not found.
        """
        try:
            from ansys.mapdl.core import get_available_ansys_installations, get_mapdl_path
            import ansys.mapdl.core as pymapdl

            installations = get_available_ansys_installations()
            if not installations:
                return None

            # Use the highest version available
            # Keys are negative of version (PyMAPDL convention: -261 = v26.1)
            version_int = abs(sorted(installations.keys())[0])
            install_path = installations[sorted(installations.keys())[0]]

            mapdl_exe = get_mapdl_path(allow_input=False)
            mapdl_exe_exists = Path(mapdl_exe).exists() if mapdl_exe else False

            # Determine if student version
            is_student = "Student" in install_path

            return AnsysInstallInfo(
                version_int=version_int,
                version_str=f"{version_int // 10}.{version_int % 10}",
                install_path=install_path,
                mapdl_exe=mapdl_exe or "",
                mapdl_exe_exists=mapdl_exe_exists,
                pymapdl_version=pymapdl.__version__,
                is_student=is_student,
                node_limit=self.STUDENT_NODE_LIMIT if is_student else None,
            )

        except ImportError:
            return None
        except Exception as e:
            print(f"[ANSYS Detection] Error: {e}")
            return None

    def get_supported_versions(self) -> list:
        """Return list of ANSYS versions supported by the installed PyMAPDL."""
        try:
            from ansys.mapdl.core import SUPPORTED_ANSYS_VERSIONS
            return list(SUPPORTED_ANSYS_VERSIONS.values())
        except Exception:
            return []
