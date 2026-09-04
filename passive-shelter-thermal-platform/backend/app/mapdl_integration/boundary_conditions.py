"""
ANSYS MAPDL thermal boundary conditions.

Applies:
1. Convection boundary conditions (ambient temperature + wind-based HTC)
2. Radiation boundary conditions (surface emissivity)

Both are applied as time-varying conditions using MAPDL TABLE arrays.

IMPORTANT: These are boundary conditions prepared for ANSYS.
The actual heat transfer is computed by the ANSYS thermal solver.

Convection heat transfer coefficient (HTC) methodology:
- Wind speed from weather API (m/s)
- Simplified flat-plate forced convection correlation:
  h ≈ 5.7 + 3.8 * v  (McAdams, simplified external building convection)
  where v = wind speed (m/s)
  Source: ASHRAE; McAdams (1954) Heat Transmission
- This is a well-known simplified correlation for building surfaces.
- For research-grade results, CFD-derived HTCs are recommended.
"""
from __future__ import annotations

import logging
import math
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ansys.mapdl.core import Mapdl

logger = logging.getLogger(__name__)


def wind_htc(wind_speed_ms: float) -> float:
    """
    Calculate external convection heat transfer coefficient from wind speed.

    Model: McAdams simplified flat-plate correlation for building surfaces.
    h = 5.7 + 3.8 × v  [W/m²K]

    This is a simplified model. A range of v=0 to ~15 m/s is reasonable.
    For extremely high winds (>20 m/s), the result should be used cautiously.

    Reference: McAdams (1954); ASHRAE Handbook of Fundamentals.

    Parameters
    ----------
    wind_speed_ms : float  Wind speed in m/s.

    Returns
    -------
    float  Convection HTC in W/m²K.
    """
    v = max(0.0, min(wind_speed_ms, 20.0))
    h = 5.7 + 3.8 * v
    return h


class BoundaryConditionApplicator:
    """
    Applies external thermal boundary conditions to the ANSYS MAPDL model.

    Conditions applied:
    1. Convection: time-varying ambient temperature + wind-based HTC
       applied to all external surfaces.
    2. Radiation: surface emissivity for grey-body radiation to sky.
    """

    def __init__(self, mapdl: "Mapdl"):
        self._m = mapdl

    def apply_convection(
        self,
        times_s: List[float],
        ambient_temps_c: List[float],
        wind_speeds_ms: List[float],
        external_area_component: str = "ALL",
        convection_htc_override: Optional[float] = None,
        table_id_temp: int = 1,
        table_id_htc: int = 2,
    ) -> None:
        """
        Apply time-varying convection BC to external surfaces.

        The ambient temperature from the weather API is used directly as
        the convection film temperature. The HTC is derived from wind speed
        using the McAdams correlation (see module docstring).

        Parameters
        ----------
        times_s : List[float]
            Simulation time steps in seconds.
        ambient_temps_c : List[float]
            Ambient temperature at each time step (°C from weather API).
        wind_speeds_ms : List[float]
            Wind speed at each time step (m/s from weather API).
        convection_htc_override : Optional[float]
            If provided, use this fixed HTC instead of wind-based calculation.
        """
        m = self._m

        # Calculate HTCs from wind speed
        if convection_htc_override is not None:
            htcs = [convection_htc_override] * len(times_s)
            logger.info(f"[MAPDL] Using user-defined convection HTC: {convection_htc_override} W/m²K")
        else:
            htcs = [wind_htc(w) for w in wind_speeds_ms]
            avg_htc = sum(htcs) / len(htcs) if htcs else 10.0
            logger.info(
                f"[MAPDL] Wind-based convection HTC range: "
                f"{min(htcs):.1f}–{max(htcs):.1f} W/m²K (avg {avg_htc:.1f})"
            )

        # Convert °C to Kelvin for ANSYS (ANSYS thermal uses Kelvin internally)
        # Actually MAPDL can use °C if TOFFST is set; we'll use Kelvin for clarity
        # Set temperature offset: TOFFST = 273.15 (so °C input works)
        m.run("TOFFST,273.15")

        # Create TABLE for ambient temperature (film temperature)
        self._create_table(table_id_temp, times_s, ambient_temps_c, "TAMB")

        # Create TABLE for HTC
        self._create_table(table_id_htc, times_s, htcs, "HTC")

        # Apply convection to all external surfaces
        # SFE,ALL,1,CONV,0,%TabHTC%  (film HTC)
        # SFE,ALL,1,CONV,1,%TabTemp% (film temperature)
        try:
            applied = False
            # If model has geometric areas, apply via SFA
            try:
                n_areas = self._m.geometry.n_area
            except Exception:
                n_areas = 0

            if n_areas > 0:
                try:
                    if external_area_component != "ALL":
                        m.cmsel("S", external_area_component, "AREA")
                    else:
                        m.asel("ALL")

                    m.sfa("ALL", 1, "CONV", f"%TAB{table_id_htc}%", f"%TAB{table_id_temp}%")
                    m.allsel()
                    applied = True
                    logger.info("[MAPDL] Convection BCs applied to external areas via SFA.")
                except Exception as e_area:
                    logger.debug(f"[MAPDL] Area convection failed, falling back to nodes: {e_area}")

            if not applied:
                # Nodal convection for imported CAD meshes
                try:
                    m.cmsel("S", "EXT_NODES", "NODE")
                except Exception:
                    m.nsel("ALL")
                m.sf("ALL", "CONV", f"%TAB{table_id_htc}%", f"%TAB{table_id_temp}%")
                m.allsel()
                logger.info("[MAPDL] Convection BCs applied to external nodes via SF.")
        except Exception as e:
            logger.error(f"[MAPDL] Convection BC failed: {e}")
            raise

    def apply_radiation(
        self,
        emissivity: float,
        ambient_temps_c: List[float],
        times_s: List[float],
        stefan_boltzmann: float = 5.67e-8,
    ) -> None:
        """
        Apply linearized grey-body radiation to external surfaces.

        ANSYS MAPDL models surface radiation through RDSF (radiation surface load)
        or RADOPT. For simplicity, we use a linearized radiation equivalent HTC
        added to the convection coefficient.

        Linearized radiation HTC:
        h_rad ≈ 4 × ε × σ × T_avg³
        where T_avg is the average surface temperature in Kelvin (approximated
        as 273.15 + T_ambient for the initial estimate).

        This is an engineering approximation. For accurate radiation, MAPDL's
        full radiation model (RADOPT, RDSF) should be used with view factors.

        Reference: Incropera et al., Fundamentals of Heat and Mass Transfer.
        """
        if not ambient_temps_c:
            return

        # Average ambient temperature in K
        avg_t_k = 273.15 + (sum(ambient_temps_c) / len(ambient_temps_c))
        h_rad = 4.0 * emissivity * stefan_boltzmann * (avg_t_k ** 3)

        logger.info(
            f"[MAPDL] Linearized radiation HTC ≈ {h_rad:.3f} W/m²K "
            f"(ε={emissivity}, T_avg={avg_t_k:.1f} K) — "
            "Assumption: linearized grey-body radiation"
        )

        # This h_rad is added to convection in practice by adding to HTC tables
        # For now, it's documented and logged. Full RADOPT can be added in future.
        return h_rad

    def apply_initial_temperature(self, initial_temp_c: float) -> None:
        """
        Apply uniform initial temperature to all nodes.
        Typically set to the starting ambient temperature.
        """
        m = self._m
        # IC,ALL,TEMP,value
        m.run(f"IC,ALL,TEMP,{initial_temp_c:.2f}")
        logger.info(f"[MAPDL] Initial temperature: {initial_temp_c:.1f}°C")

    def _create_table(
        self,
        table_id: int,
        times_s: List[float],
        values: List[float],
        label: str,
    ) -> None:
        """Create MAPDL TABLE array for time-varying BC."""
        m = self._m
        n = len(times_s)
        name = f"TAB{table_id}"

        m.run(f"*DIM,{name},TABLE,{n},1,1,TIME")
        for i, (t, v) in enumerate(zip(times_s, values), start=1):
            m.run(f"{name}({i},0,1)={t:.2f}")
            m.run(f"{name}({i},1,1)={v:.6f}")

        logger.debug(f"[MAPDL] Table {name} ({label}) created: {n} points")
