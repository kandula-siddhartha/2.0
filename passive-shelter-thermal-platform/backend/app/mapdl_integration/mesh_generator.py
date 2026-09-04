"""
ANSYS MAPDL mesh generation for shelter thermal model.

Uses MAPDL's automatic meshing (SMESH/VMESH) with size controls.
Element type: SOLID70 (8-node thermal hexahedral/tetrahedral).

Node limit awareness: ANSYS Student v26.1 ~128,000 nodes.
The mesh size is checked to avoid exceeding this limit.
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ansys.mapdl.core import Mapdl

logger = logging.getLogger(__name__)

STUDENT_NODE_LIMIT = 128_000


class MeshGenerator:
    """
    Generates a thermal finite element mesh in ANSYS MAPDL.
    """

    def __init__(self, mapdl: "Mapdl", is_student: bool = True):
        self._m = mapdl
        self._is_student = is_student

    def generate_mesh(
        self,
        element_size: float = 0.30,
        mesh_type: str = "auto",
    ) -> dict:
        """
        Generate mesh for all volumes.

        Parameters
        ----------
        element_size : float
            Target element edge length in meters.
            Larger = fewer nodes (safer for Student license).
        mesh_type : str
            'auto' uses MSHAPE,0,3D (hex-dominant) or MSHAPE,1,3D (tet)

        Returns
        -------
        dict with 'node_count', 'element_count', 'mesh_quality'
        """
        m = self._m

        logger.info(f"[MAPDL] Generating mesh with element size {element_size}m")

        # Set element size
        m.esize(element_size)

        # Use tetrahedral meshing (more robust for complex shapes)
        m.mshape(1, "3D")    # 1 = tet, 3D elements
        m.mshkey(0)          # 0 = free meshing

        # Mesh all volumes
        m.allsel()
        m.vmesh("ALL")

        # Query mesh statistics
        node_count = m.mesh.n_node
        element_count = m.mesh.n_elem

        logger.info(f"[MAPDL] Mesh complete: {node_count} nodes, {element_count} elements")

        # Check Student node limit
        if self._is_student and node_count > STUDENT_NODE_LIMIT:
            raise RuntimeError(
                f"ANSYS Student node limit exceeded: {node_count} > {STUDENT_NODE_LIMIT}. "
                f"Increase element_size (currently {element_size}m) to reduce node count. "
                f"Suggested: element_size ≥ {element_size * (node_count / STUDENT_NODE_LIMIT):.2f}m"
            )

        return {
            "node_count": node_count,
            "element_count": element_count,
            "element_size": element_size,
        }

    def refine_mesh(self, area_component: str, level: int = 1) -> None:
        """
        Apply local mesh refinement to a named area component.
        Used to refine external surfaces for better BC accuracy.
        """
        m = self._m
        m.cmsel("S", area_component, "AREA")
        m.arefine("ALL", "", "", level, "ALL")
        m.allsel()
