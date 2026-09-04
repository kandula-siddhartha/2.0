"""
ANSYS MAPDL solar load application.

Applies time-varying solar heat flux to shelter surfaces using MAPDL
surface load (SFE) commands with tabular input (TABLE arrays).

The solar load is based on:
1. API-provided shortwave radiation values (W/m²) — from weather data
2. Material solar absorptivity — fraction of radiation absorbed
3. Surface orientation — exposure factor based on orientation and sun position

IMPORTANT: This prepares boundary conditions for ANSYS. The actual thermal
effect of the solar load is computed by the ANSYS solver, not this code.

Methodology:
- Global horizontal irradiance (GHI) from weather API
- Simple orientation factor: south-facing receives highest gain
- Net heat flux to surface = GHI × absorptivity × orientation_factor
"""
from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ansys.mapdl.core import Mapdl

logger = logging.getLogger(__name__)


def orientation_factor(surface_orientation: str, solar_azimuth_deg: float = 180.0) -> float:
    """
    Calculate an approximate solar incidence factor based on surface orientation.

    Assumptions (documented):
    - This is a simplified geometric factor, not a rigorous solar angle calculation.
    - For more accurate results, direct normal irradiance and full solar position
      calculations should be used in a future version.
    - South-facing surfaces receive maximum solar input in the northern hemisphere.

    Parameters
    ----------
    surface_orientation : str
        'south', 'north', 'east', 'west', or an angle in degrees.
    solar_azimuth_deg : float
        Solar azimuth angle (approximate, 180° = solar noon, direct south).

    Returns
    -------
    float : 0.0 to 1.0 — fraction of horizontal radiation reaching this surface.
    """
    orient_map = {
        "south": 1.0,
        "north": 0.05,   # Very limited direct solar for north-facing in NH
        "east": 0.45,    # Morning sun
        "west": 0.45,    # Afternoon sun
    }
    if isinstance(surface_orientation, str) and surface_orientation.lower() in orient_map:
        return orient_map[surface_orientation.lower()]
    # Try to parse as angle (degrees from north, clockwise)
    try:
        angle = float(surface_orientation)
        # Factor based on angle difference from solar azimuth (simplified)
        diff = abs(angle - solar_azimuth_deg)
        if diff > 180:
            diff = 360 - diff
        return max(0.0, math.cos(math.radians(diff)))
    except (ValueError, TypeError):
        return 0.5  # Default if unrecognized


class SolarLoadApplicator:
    """
    Applies time-varying solar heat flux boundary conditions to ANSYS MAPDL.

    Uses MAPDL TABLE arrays to represent time-varying solar heat flux.
    The TABLE is then applied to surfaces using the SFE (Surface Force Element) command.
    """

    def __init__(self, mapdl: "Mapdl"):
        self._m = mapdl

    def apply_solar_load(
        self,
        times_s: List[float],
        solar_radiation_wm2: List[float],
        solar_absorptivity: float,
        ambient_temps_c: Optional[List[float]] = None,
        wind_speeds_ms: Optional[List[float]] = None,
        convection_htc_override: Optional[float] = None,
        roof_area_component: str = "ROOF_AREAS",
        south_area_component: str = "SOUTH_AREAS",
        roof_orientation: str = "horizontal",
        wall_orientation: str = "south",
        table_id_roof: int = 10,
        table_id_south: int = 11,
        table_id_htc: int = 12,
    ) -> None:
        """
        Apply solar radiation using the ASHRAE Sol-Air temperature formulation.
        
        T_sol_air = T_ambient + (absorptivity * I_solar) / h_c
        
        Applying Sol-Air temperature to the convection film boundary condition
        ensures that solar radiation is accurately introduced while maintaining
        convective wind cooling to ambient air, preventing MAPDL boundary condition
        overrides and unphysical temperature runaway on low-mass/low-k materials.
        """
        m = self._m

        logger.info("[MAPDL] Applying ASHRAE Sol-Air solar boundary conditions")
        peak_solar = max(solar_radiation_wm2) if solar_radiation_wm2 else 0.0
        logger.info(
            f"  Peak solar radiation: {peak_solar:.1f} W/m²"
            f" (absorptivity: {solar_absorptivity:.2f})"
        )

        # Compute convection coefficients (HTC)
        if convection_htc_override is not None:
            htcs = [convection_htc_override] * len(times_s)
        elif wind_speeds_ms and len(wind_speeds_ms) == len(times_s):
            htcs = [max(5.0, min(35.0, 5.7 + 3.8 * max(0.0, min(w, 20.0)))) for w in wind_speeds_ms]
        else:
            htcs = [12.0] * len(times_s)

        self._create_table(table_id_htc, times_s, htcs, label="SOLAR_HTC")

        # Compute Sol-Air film temperatures
        amb_temps = ambient_temps_c if (ambient_temps_c and len(ambient_temps_c) == len(times_s)) else [20.0] * len(times_s)
        wall_factor = orientation_factor(wall_orientation)

        roof_sol_air = []
        south_sol_air = []
        for q, h, t_amb in zip(solar_radiation_wm2, htcs, amb_temps):
            h_eff = max(4.0, h)
            # Sol-air formula: T_amb + alpha * I / h_c
            t_roof = t_amb + (solar_absorptivity * q * 1.0) / h_eff
            t_south = t_amb + (solar_absorptivity * q * wall_factor) / h_eff
            roof_sol_air.append(t_roof)
            south_sol_air.append(t_south)

        self._create_table(table_id_roof, times_s, roof_sol_air, label="SOL_AIR_ROOF")
        self._create_table(table_id_south, times_s, south_sol_air, label="SOL_AIR_SOUTH")

        # ── Apply to roof surfaces/nodes via Convection (Preserves Air Cooling) ─
        applied_roof = False
        try:
            m.cmsel("S", roof_area_component, "AREA")
            m.sfa("ALL", 1, "CONV", f"%TAB{table_id_htc}%", f"%TAB{table_id_roof}%")
            m.allsel()
            applied_roof = True
            logger.info(f"[MAPDL] Sol-Air convection applied to area component {roof_area_component}")
        except Exception:
            pass

        if not applied_roof:
            try:
                m.cmsel("S", "ROOF_NODES", "NODE")
                m.sf("ALL", "CONV", f"%TAB{table_id_htc}%", f"%TAB{table_id_roof}%")
                m.allsel()
                logger.info("[MAPDL] Sol-Air convection applied to node component ROOF_NODES")
            except Exception as e:
                logger.warning(f"[MAPDL] Could not apply roof sol-air load: {e}")

        # ── Apply to south facade surfaces/nodes via Convection ────────────────
        applied_south = False
        try:
            m.cmsel("S", south_area_component, "AREA")
            m.sfa("ALL", 1, "CONV", f"%TAB{table_id_htc}%", f"%TAB{table_id_south}%")
            m.allsel()
            applied_south = True
            logger.info(f"[MAPDL] Sol-Air convection applied to area component {south_area_component}")
        except Exception:
            pass

        if not applied_south:
            try:
                m.cmsel("S", "SOUTH_NODES", "NODE")
                m.sf("ALL", "CONV", f"%TAB{table_id_htc}%", f"%TAB{table_id_south}%")
                m.allsel()
                logger.info("[MAPDL] Sol-Air convection applied to node component SOUTH_NODES")
            except Exception as e:
                logger.warning(f"[MAPDL] Could not apply south facade sol-air load: {e}")

    def _create_table(
        self,
        table_id: int,
        times_s: List[float],
        values: List[float],
        label: str = "TABLE",
    ) -> None:
        """
        Create a MAPDL TABLE array for time-varying boundary conditions.

        MAPDL TABLE arrays:
        *DIM,TableName,TABLE,nrows,ncols,1,TIME
        Row index 0 = time values
        Data values = corresponding BC values
        """
        m = self._m
        n = len(times_s)
        name = f"TAB{table_id}"

        m.run(f"*DIM,{name},TABLE,{n},1,1,TIME")
        for i, (t, v) in enumerate(zip(times_s, values), start=1):
            m.run(f"{name}({i},0,1)={t:.2f}")  # Time row
            m.run(f"{name}({i},1,1)={v:.4f}")  # Value row

        logger.debug(f"[MAPDL] Table {name} created with {n} points, label={label}")
