"""
FastAPI router for ANSYS connection status, discovery, and path configuration.
"""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from ..schemas.schemas import AnsysStatusResponse, AnsysConfigRequest
from ..mapdl_integration.version_detection import AnsysVersionDetector, AnsysInstallInfo
from ..mapdl_integration.connection import test_ansys_connection
from ..config import settings

router = APIRouter(prefix="/api/v1/ansys", tags=["ANSYS Connection"])
_detector = AnsysVersionDetector()

_PYMAPDL_VERSION = "0.74.1"


def _get_pymapdl_version() -> str:
    """Get PyMAPDL version by reading from the installed package metadata."""
    try:
        import importlib.metadata
        return importlib.metadata.version("ansys-mapdl-core")
    except Exception:
        return _PYMAPDL_VERSION


def _get_active_info() -> tuple[AnsysInstallInfo | None, str]:
    """Retrieve active ANSYS info using settings.ansys_mapdl_exe or dynamic detection."""
    pymapdl_ver = _get_pymapdl_version()
    if settings.ansys_mapdl_exe and Path(settings.ansys_mapdl_exe).exists():
        info = _detector.inspect_path(settings.ansys_mapdl_exe)
        if info:
            return info, pymapdl_ver

    info = _detector.detect()
    if info:
        settings.ansys_mapdl_exe = info.mapdl_exe
        settings.ansys_install_path = info.install_path
        settings.ansys_version = info.version_int
    return info, pymapdl_ver


@router.get("/status", response_model=AnsysStatusResponse)
def get_ansys_status():
    """Check ANSYS installation status and PyMAPDL availability."""
    info, pymapdl_ver = _get_active_info()

    return AnsysStatusResponse(
        ansys_detected=info is not None,
        ansys_version=info.version_str if info else None,
        ansys_install_path=info.install_path if info else None,
        mapdl_exe_path=info.mapdl_exe if info else (settings.ansys_mapdl_exe or None),
        mapdl_exe_exists=info.mapdl_exe_exists if info else False,
        pymapdl_version=pymapdl_ver,
        pymapdl_available=True,
        connection_tested=False,
        student_license=info.is_student if info else False,
        node_limit=info.node_limit if info else None,
    )


@router.post("/auto-detect", response_model=AnsysStatusResponse)
def auto_detect_ansys():
    """Perform a deep scan of drives and environment variables for ANSYS."""
    info = _detector.detect()
    pymapdl_ver = _get_pymapdl_version()

    if info and info.mapdl_exe_exists:
        settings.save_ansys_path(info.mapdl_exe)
        return AnsysStatusResponse(
            ansys_detected=True,
            ansys_version=info.version_str,
            ansys_install_path=info.install_path,
            mapdl_exe_path=info.mapdl_exe,
            mapdl_exe_exists=True,
            pymapdl_version=pymapdl_ver,
            pymapdl_available=True,
            connection_tested=False,
            student_license=info.is_student,
            node_limit=info.node_limit,
        )

    return AnsysStatusResponse(
        ansys_detected=False,
        ansys_version=None,
        ansys_install_path=None,
        mapdl_exe_path=None,
        mapdl_exe_exists=False,
        pymapdl_version=pymapdl_ver,
        pymapdl_available=True,
        connection_tested=False,
        connection_successful=False,
        connection_error="Automatic discovery could not find an ANSYS installation on this laptop. Please specify the path manually.",
    )


@router.post("/configure", response_model=AnsysStatusResponse)
def configure_ansys_path(req: AnsysConfigRequest):
    """
    Set and validate a user-specified ANSYS executable or install path,
    activating it immediately and optionally testing live connection.
    """
    cleaned_path = req.exe_path.strip().strip('"').strip("'")
    if not cleaned_path:
        raise HTTPException(status_code=400, detail="Executable path cannot be empty.")

    info = _detector.inspect_path(cleaned_path)
    pymapdl_ver = _get_pymapdl_version()

    if not info or not info.mapdl_exe_exists:
        return AnsysStatusResponse(
            ansys_detected=False,
            ansys_version=None,
            ansys_install_path=None,
            mapdl_exe_path=cleaned_path,
            mapdl_exe_exists=False,
            pymapdl_version=pymapdl_ver,
            pymapdl_available=True,
            connection_tested=True,
            connection_successful=False,
            connection_error=f"No valid ANSYS executable (ansysXXX.exe) found at: {cleaned_path}",
        )

    # Save and activate path
    settings.save_ansys_path(info.mapdl_exe)

    # Live test if requested
    if req.test_now:
        success, version, error = test_ansys_connection(exe_path=info.mapdl_exe)
        return AnsysStatusResponse(
            ansys_detected=True,
            ansys_version=info.version_str,
            ansys_install_path=info.install_path,
            mapdl_exe_path=info.mapdl_exe,
            mapdl_exe_exists=True,
            pymapdl_version=pymapdl_ver,
            pymapdl_available=True,
            connection_tested=True,
            connection_successful=success,
            connection_error=error,
            student_license=info.is_student,
            node_limit=info.node_limit,
        )

    return AnsysStatusResponse(
        ansys_detected=True,
        ansys_version=info.version_str,
        ansys_install_path=info.install_path,
        mapdl_exe_path=info.mapdl_exe,
        mapdl_exe_exists=True,
        pymapdl_version=pymapdl_ver,
        pymapdl_available=True,
        connection_tested=False,
        student_license=info.is_student,
        node_limit=info.node_limit,
    )


@router.post("/test-connection", response_model=AnsysStatusResponse)
def test_connection():
    """
    Launch MAPDL and verify live connectivity.
    """
    info, pymapdl_ver = _get_active_info()

    if not info:
        return AnsysStatusResponse(
            ansys_detected=False,
            pymapdl_available=True,
            pymapdl_version=pymapdl_ver,
            connection_tested=True,
            connection_successful=False,
            connection_error="No ANSYS installation detected. Please configure the executable path.",
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
