"""
ANSYS MAPDL thermal material assignment.
Maps material library properties to MAPDL material commands.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ansys.mapdl.core import Mapdl

logger = logging.getLogger(__name__)


class MaterialMapper:
    """
    Assigns thermal material properties to ANSYS MAPDL.

    MAPDL thermal material properties used:
    - MP,KXX: thermal conductivity (W/m·K)
    - MP,DENS: density (kg/m³)
    - MP,C: specific heat (J/kg·K)
    - MP,EMIS: emissivity (for radiation)
    """

    def __init__(self, mapdl: "Mapdl"):
        self._m = mapdl

    def assign_material(
        self,
        mat_num: int,
        thermal_conductivity: float,
        density: float,
        specific_heat: float,
        emissivity: float = 0.9,
        name: str = "Material",
    ) -> None:
        """
        Assign thermal properties to a MAPDL material number.

        Parameters
        ----------
        mat_num : int
            MAPDL material reference number (1-based).
        thermal_conductivity : float
            Isotropic thermal conductivity in W/m·K.
        density : float
            Mass density in kg/m³.
        specific_heat : float
            Specific heat capacity in J/kg·K.
        emissivity : float
            Surface emissivity (0-1).
        name : str
            Human-readable material name (used in logging).
        """
        m = self._m

        logger.info(
            f"[MAPDL] Assigning material {mat_num}: {name} "
            f"(k={thermal_conductivity} W/mK, rho={density} kg/m3, "
            f"Cp={specific_heat} J/kgK, emis={emissivity})"
        )

        # Assign material properties via explicit APDL commands
        m.run(f"MP,KXX,{mat_num},{thermal_conductivity}")
        m.run(f"MP,DENS,{mat_num},{density}")
        m.run(f"MP,C,{mat_num},{specific_heat}")
        m.run(f"MP,EMIS,{mat_num},{emissivity}")

    def assign_material_to_volumes(
        self,
        mat_num: int,
        volume_nums: list,
    ) -> None:
        """Assign a material number to selected MAPDL volumes."""
        m = self._m
        m.vsel("NONE")
        for v in volume_nums:
            m.vsel("A", "VOLU", "", v)
        m.run(f"VATT,{mat_num},,1")
        m.allsel()

    def assign_material_to_all(self, mat_num: int) -> None:
        """Assign material to all currently selected volumes."""
        m = self._m
        m.allsel()
        m.run(f"VATT,{mat_num},,1")
