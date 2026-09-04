"""
ANSYS MAPDL parametric shelter geometry builder.

Builds a 3D solid shelter geometry using APDL primitives (BLOCK command).
The shelter consists of:
  - 4 walls (north, south, east, west)
  - Roof slab
  - Floor slab
  - Interior air volume

All geometry is specified in meters (SI units).
Element type: SOLID70 (8-node thermal solid) for linear,
              or SOLID90 (20-node) for higher accuracy.

NOTE: ANSYS Student v26.1 node limit ~128,000. Mesh size is chosen
to keep well within this limit.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ansys.mapdl.core import Mapdl

logger = logging.getLogger(__name__)


@dataclass
class ShelterGeometry:
    """Parameters defining the parametric shelter geometry."""
    # External dimensions (m)
    length: float = 5.0       # X direction
    width: float = 4.0        # Y direction  
    height: float = 3.0       # Z direction

    wall_thickness: float = 0.30
    roof_thickness: float = 0.25
    floor_thickness: float = 0.20

    # Orientation angle from north (degrees), 0=North, 90=East, 180=South, 270=West
    orientation_deg: float = 180.0  # South-facing default


class ShelterModelBuilder:
    """
    Builds ANSYS MAPDL thermal model for a parametric shelter.

    The shelter is modeled as a set of 3D solid volumes:
    - Structural walls, roof, floor using the selected material
    - Interior volume for temperature monitoring

    APDL commands used:
    - BLOCK: creates rectangular solid volumes
    - VSBV: subtracts volumes to create hollow shell
    - Component selection for result extraction
    """

    # ANSYS element types
    ET_SOLID70 = 70    # 8-node thermal solid (linear)
    ET_SOLID90 = 90    # 20-node thermal solid (quadratic)

    def __init__(self, mapdl: "Mapdl"):
        self._m = mapdl

    def build(self, geom: ShelterGeometry) -> dict:
        """
        Build the parametric shelter in ANSYS.

        Returns
        -------
        dict with:
            'exterior_vnum': volume number for exterior shell
            'interior_vnum': volume number for interior air
            'exterior_areas': list of external surface area numbers
            'interior_areas': list of interior surface area numbers
            'south_areas': area numbers of south-facing surfaces
            'roof_areas': area numbers of roof surfaces
            'wall_vols': list of wall volume numbers
            'interior_vol': interior air volume number
        """
        m = self._m
        g = geom

        logger.info(f"[MAPDL] Building shelter geometry: {g.length}×{g.width}×{g.height} m")

        # ── 1. Reset and set preferences ──────────────────────────────────────
        m.run("/PREP7")
        m.run("/UNITS,SI")
        m.run("ET,1,SOLID70")   # 8-node thermal solid

        # ── 2. Build outer shell geometry ──────────────────────────────────────
        # Outer box (exterior dimensions)
        ox1, oy1, oz1 = 0.0, 0.0, 0.0
        ox2 = g.length
        oy2 = g.width
        oz2 = g.height + g.floor_thickness + g.roof_thickness

        m.block(ox1, ox2, oy1, oy2, oz1, oz2)
        outer_vol = 1

        # ── 3. Build inner void ────────────────────────────────────────────────
        wt = g.wall_thickness
        ft = g.floor_thickness
        rt = g.roof_thickness

        ix1 = wt
        ix2 = g.length - wt
        iy1 = wt
        iy2 = g.width - wt
        iz1 = ft
        iz2 = g.height + ft

        m.block(ix1, ix2, iy1, iy2, iz1, iz2)
        inner_vol = 2

        # ── 4. Subtract inner from outer to get shell ─────────────────────────
        m.run("VSBV,1,2,,,KEEP")   # Subtract, keep both originals for reference
        # After VSBV: volume 3 = shell (walls + roof + floor)
        # Volume 2 = interior void (retained)
        shell_vol = 3

        # ── 5. Glue volumes so they share nodes at interfaces ─────────────────
        m.vglue("ALL")

        # ── 6. Select areas and create named components ───────────────────────
        # Select all exterior surfaces for boundary conditions
        m.asel("ALL")
        m.cm("EXT_SURFACES", "AREA")

        # ── 7. Create component for interior volume (for temp monitoring) ─────
        m.vsel("S", "VOLU", "", inner_vol)
        m.cm("INTERIOR_VOL", "VOLU")
        m.allsel()

        # ── 8. Create named selection for roof (top surfaces) ────────────────
        # Roof: areas at z = oz2
        top_z = oz2
        m.asel("S", "LOC", "Z", top_z - 0.001, top_z + 0.001)
        m.cm("ROOF_AREAS", "AREA")
        m.allsel()

        # ── 9. South-facing surfaces ──────────────────────────────────────────
        # South = minimum Y face (y = 0)
        m.asel("S", "LOC", "Y", -0.001, 0.001)
        m.cm("SOUTH_AREAS", "AREA")
        m.allsel()

        # ── 10. North-facing surfaces ─────────────────────────────────────────
        m.asel("S", "LOC", "Y", oy2 - 0.001, oy2 + 0.001)
        m.cm("NORTH_AREAS", "AREA")
        m.allsel()

        logger.info("[MAPDL] Geometry built successfully.")

        return {
            "outer_vol": outer_vol,
            "inner_vol": inner_vol,
            "shell_vol": shell_vol,
            "interior_dims": {
                "x1": ix1, "x2": ix2,
                "y1": iy1, "y2": iy2,
                "z1": iz1, "z2": iz2,
            },
        }
