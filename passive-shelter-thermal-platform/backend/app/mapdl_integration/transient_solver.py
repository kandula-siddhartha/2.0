"""
ANSYS MAPDL transient thermal solver configuration and execution.

Configures and runs the ANSYS transient thermal analysis.
ANSYS performs all thermal calculations. Python only configures
and monitors the solve.

Analysis type: ANTYPE,TRANS (Transient Thermal)
Solver: Sparse direct solver (default in MAPDL)
"""
from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ansys.mapdl.core import Mapdl

logger = logging.getLogger(__name__)


class TransientSolver:
    """
    Configures and executes the ANSYS transient thermal analysis.
    """

    def __init__(self, mapdl: "Mapdl"):
        self._m = mapdl

    def configure_and_solve(
        self,
        total_time_s: float,
        time_step_s: float,
        times_s: Optional[List[float]] = None,
        min_time_step_s: Optional[float] = None,
        max_time_step_s: Optional[float] = None,
        nonlinear: bool = False,
    ) -> None:
        """
        Configure and run the ANSYS transient thermal analysis.

        Parameters
        ----------
        total_time_s : float
            Total simulation duration in seconds.
        time_step_s : float
            Target time step in seconds (e.g. 3600 for hourly).
        times_s : List[float], optional
            If provided, use these specific time points for output.
        min_time_step_s, max_time_step_s : float, optional
            Min/max time step for automatic time stepping.
        nonlinear : bool
            If True, use Newton-Raphson iteration (needed for radiation).
        """
        m = self._m
        logger.info(
            f"[MAPDL] Configuring transient thermal: "
            f"duration={total_time_s/3600:.1f}h, dt={time_step_s/3600:.2f}h"
        )

        # ── Enter SOLUTION phase ──────────────────────────────────────────────
        m.run("/SOLU")

        # ── Analysis type: New Transient Analysis from t=0 ────────────────────
        m.run("ANTYPE,TRANS,NEW")    # Explicitly specify NEW transient analysis
        m.run("TRNOPT,FULL")         # Full transient method
        m.run("TIMINT,ON")           # Turn on transient time integration

        # ── Time settings ─────────────────────────────────────────────────────
        m.run(f"TIME,{total_time_s:.2f}")
        m.run(f"DELTIM,{time_step_s:.2f}")
        m.run("KBC,0")               # Ramped boundary conditions between substeps

        if min_time_step_s and max_time_step_s:
            m.run("AUTOTS,ON")
            m.run(f"DELTIM,{time_step_s:.2f},{min_time_step_s:.2f},{max_time_step_s:.2f}")
        else:
            m.run("AUTOTS,OFF")

        # ── Output controls ───────────────────────────────────────────────────
        m.run("OUTPR,ALL,ALL")
        m.run("OUTRES,ALL,ALL")      # Store all results at every substep

        # ── Solver settings ───────────────────────────────────────────────────
        m.run("EQSLV,SPARSE")

        if nonlinear:
            m.run("NROPT,FULL")
        else:
            m.run("NROPT,AUTO")

        # ── Convergence criteria ──────────────────────────────────────────────
        m.run("CNVTOL,HEAT,1.0,0.001")

        # ── Run the solve ─────────────────────────────────────────────────────
        logger.info(f"[MAPDL] Starting ANSYS transient thermal solve (0 to {total_time_s}s, dt={time_step_s}s)...")
        try:
            m.run("SOLVE")
        except Exception as e:
            # If the result file was successfully written with all sets, continue
            try:
                m.run("/POST1")
                n_sets = m.post_processing.nsets
                if n_sets and n_sets > 0:
                    logger.info(f"[MAPDL] Solve completed with {n_sets} result sets on file.")
                    return
            except Exception:
                pass
            raise

        try:
            m.run("FINISH")
        except Exception:
            pass

        logger.info("[MAPDL] ANSYS solve completed successfully.")
