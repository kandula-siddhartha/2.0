"""
PyMAPDL connection management.
Handles launching, connecting to, and managing ANSYS MAPDL sessions.

IMPORTANT: This module is the ONLY gateway to ANSYS. All thermal simulation
must flow through this layer. ANSYS performs the actual thermal simulation;
Python only orchestrates it.
"""
from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ansys.mapdl.core import Mapdl

logger = logging.getLogger(__name__)


class AnsysConnectionError(Exception):
    """Raised when ANSYS cannot be connected to or started."""
    pass


class MAPDLSession:
    """
    Wrapper around a PyMAPDL Mapdl instance.
    Provides clean start/stop lifecycle and connection testing.
    """

    def __init__(
        self,
        exe_path: Optional[str] = None,
        run_location: Optional[str] = None,
        port: int = 50052,
        start_timeout: int = 120,
        nproc: int = 1,
        verbose: bool = False,
    ):
        self._exe_path = exe_path
        self._run_location = run_location
        self._port = port
        self._start_timeout = start_timeout
        self._nproc = nproc
        self._verbose = verbose
        self._mapdl: Optional["Mapdl"] = None

    @property
    def mapdl(self) -> "Mapdl":
        if self._mapdl is None:
            raise AnsysConnectionError("MAPDL session is not started. Call start() first.")
        return self._mapdl

    @property
    def is_alive(self) -> bool:
        if self._mapdl is None:
            return False
        try:
            self._mapdl.inquire("", "VERSION")
            return True
        except Exception:
            return False

    def start(self) -> None:
        """
        Launch a local ANSYS MAPDL instance using PyMAPDL gRPC mode.
        Raises AnsysConnectionError if startup fails.
        """
        try:
            from ansys.mapdl.core import launch_mapdl
        except ImportError as e:
            raise AnsysConnectionError(
                "PyMAPDL (ansys-mapdl-core) is not installed. "
                "Install it with: pip install ansys-mapdl-core"
            ) from e

        launch_kwargs = {
            "port": self._port,
            "start_timeout": self._start_timeout,
            "nproc": self._nproc,
            "ram": 1024,
            "override": True,
            "print_com": self._verbose,
            "log_apdl": "w" if self._verbose else None,
        }

        if self._exe_path and Path(self._exe_path).exists():
            launch_kwargs["exec_file"] = self._exe_path

        if self._run_location:
            Path(self._run_location).mkdir(parents=True, exist_ok=True)
            launch_kwargs["run_location"] = self._run_location

        logger.info(f"[MAPDL] Launching MAPDL on port {self._port}...")

        try:
            self._mapdl = launch_mapdl(**launch_kwargs)
            logger.info(f"[MAPDL] Connected. Version: {self._mapdl.version}")
        except Exception as e:
            raise AnsysConnectionError(
                f"ANSYS MAPDL could not be started. "
                f"Verify ANSYS is installed and licensed. Details: {e}"
            ) from e

    def close(self) -> None:
        """Gracefully close the MAPDL session."""
        if self._mapdl is not None:
            try:
                self._mapdl.exit()
                logger.info("[MAPDL] Session closed.")
            except Exception as e:
                logger.warning(f"[MAPDL] Error during close: {e}")
            finally:
                self._mapdl = None

    def __enter__(self) -> "MAPDLSession":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.close()


def test_ansys_connection(
    exe_path: Optional[str] = None,
    run_location: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Test ANSYS connectivity by launching MAPDL and running a minimal command.

    Returns
    -------
    (success, version_string, error_message)
    """
    session = MAPDLSession(exe_path=exe_path, run_location=run_location)
    try:
        session.start()
        version = str(session.mapdl.version)
        session.close()
        return True, version, None
    except AnsysConnectionError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, f"Unexpected error: {e}"
    finally:
        session.close()
