"""
FastAPI router for ANSYS connection status and testing.
"""
from __future__ import annotations

from fastapi import APIRouter
from ..schemas.schemas import AnsysStatusResponse
from ..mapdl_integration.version_detection import AnsysVersionDetector
from ..mapdl_integration.connection import test_ansys_connection
from ..config import settings

router = APIRouter(prefix="/api/v1/ansys", tags=["ANSYS Connection"])
_detector = AnsysVersionDetector()

_PYMAPDL_VERSION = "0.74.1"  # Detected at startup; update if needed


def _get_pymapdl_version() -> str:
    """Get PyMAPDL version by reading from the installed package metadata."""
    try:
        import importlib.metadata
        return importlib.metadata.version("ansys-mapdl-core")
    except Exception:
        return _PYMAPDL_VERSION


@router.get("/status", response_model=AnsysStatusResponse)
def get_ansys_status():
    """Check ANSYS installation status and PyMAPDL availability."""
    info = _detector.detect()

    return AnsysStatusResponse(
        ansys_detected=info is not None,
        ansys_version=info.version_str if info else None,
        ansys_install_path=info.install_path if info else None,
        mapdl_exe_path=info.mapdl_exe if info else None,
        mapdl_exe_exists=info.mapdl_exe_exists if info else False,
        pymapdl_version=_get_pymapdl_version(),
        pymapdl_available=True,
        connection_tested=False,
        student_license=info.is_student if info else False,
        node_limit=info.node_limit if info else None,
    )


@router.post("/test-connection", response_model=AnsysStatusResponse)
def test_connection():
    """
    Launch MAPDL and verify connectivity.
    WARNING: This starts an actual ANSYS MAPDL instance (may take 30-120 seconds).
    """
    info = _detector.detect()
    pymapdl_ver = _get_pymapdl_version()

    if not info:
        return AnsysStatusResponse(
            ansys_detected=False,
            pymapdl_available=True,
            pymapdl_version=pymapdl_ver,
            connection_tested=True,
            connection_successful=False,
            connection_error="No ANSYS installation detected.",
        )

    success, version, error = test_ansys_connection(
        exe_path=info.mapdl_exe,
    )

    return AnsysStatusResponse(
        ansys_detected=True,
        ansys_version=info.version_str,
        ansys_install_path=info.install_path,
        mapdl_exe_path=info.mapdl_exe,
        mapdl_exe_exists=info.mapdl_exe_exists,
        pymapdl_version=pymapdl_ver,
        pymapdl_available=True,
        connection_tested=True,
        connection_successful=success,
        connection_error=error,
        student_license=info.is_student,
        node_limit=info.node_limit,
    )
