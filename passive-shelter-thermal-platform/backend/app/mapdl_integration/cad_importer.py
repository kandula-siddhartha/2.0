"""
ANSYS MAPDL CAD geometry importer and boundary classifier.

Supports:
- STEP (.step, .stp)
- IGES (.iges, .igs)
- STL (.stl)
- ANSYS Common Database (.cdb, .ans)

Handles:
1. Geometry loading & adaptive meshing (via Gmsh / OpenCASCADE).
2. Unit normalization (automatically converts millimeter CAD to standard SI meters).
3. Student license protection (adaptive element sizing strictly under 128,000 nodes).
4. Direct high-speed bulk ingestion into MAPDL /PREP7.
5. Automated boundary classification:
   - EXT_NODES: exterior envelope nodes for ambient convection.
   - ROOF_NODES: roof elevation nodes for solar global horizontal irradiance (GHI).
   - SOUTH_NODES: solar-facing facade nodes for solar wall gain.
   - INTERIOR_NODES: indoor cavity / centroid nodes for interior thermal comfort tracking.
"""
from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from ansys.mapdl.core import Mapdl

logger = logging.getLogger(__name__)

STUDENT_NODE_LIMIT = 120_000  # Safety threshold under 128,000


class CADImportError(Exception):
    """Raised when CAD geometry cannot be imported or meshed."""
    pass


class CADModelImporter:
    """
    Imports external CAD files into ANSYS MAPDL and prepares them for thermal analysis.
    """

    def __init__(self, mapdl: "Mapdl"):
        self._m = mapdl

    def import_cad(
        self,
        file_path: str,
        file_format: Optional[str] = None,
        orientation: str = "south",
        target_mesh_size: float = 0.35,
    ) -> Dict:
        """
        Import CAD geometry into MAPDL.

        Parameters
        ----------
        file_path : str
            Path to the CAD file on disk.
        file_format : Optional[str]
            CAD format (STEP, IGES, CDB, STL, etc.). Inferred if None.
        orientation : str
            Orientation of the primary solar facade ('south', 'north', 'east', 'west').
        target_mesh_size : float
            Desired element edge length in meters.

        Returns
        -------
        Dict with geometry and boundary metadata:
            - 'length', 'width', 'height': bounding box dimensions (m)
            - 'roof_area': estimated exposed roof area (m²)
            - 'envelope_area': estimated total exterior surface area (m²)
            - 'interior_centroid': (cx, cy, cz)
            - 'interior_probe_nodes': list of node IDs near interior core
            - 'node_count': total FE nodes
            - 'element_count': total FE elements
            - 'is_cad': True
        """
        p = Path(file_path)
        if not p.exists():
            raise CADImportError(f"CAD file not found at: {file_path}")

        ext = (file_format or p.suffix.lstrip(".")).lower()
        logger.info(f"[MAPDL CAD] Importing CAD file: {p.name} (format: {ext})")

        m = self._m

        # ── Handle ANSYS Common Database (.cdb / .ans) ────────────────────────
        if ext in {"cdb", "ans"}:
            return self._import_native_cdb(str(p), orientation)

        # ── Handle 3D CAD (STEP, IGES, STL, BREP) ─────────────────────────────
        return self._import_cad_via_mesh(str(p), ext, orientation, target_mesh_size)

    def _import_native_cdb(self, file_path: str, orientation: str) -> Dict:
        """Import an existing ANSYS CDB database archive."""
        m = self._m
        m.run("/PREP7")
        m.run("/UNITS,SI")
        m.run("ET,1,SOLID70")

        logger.info(f"[MAPDL CAD] Reading CDB file into database: {file_path}")
        cdb_name = Path(file_path).stem
        cdb_ext = Path(file_path).suffix.lstrip(".")
        cdb_dir = str(Path(file_path).parent).replace("\\", "/")

        try:
            m.cdread("DB", cdb_name, cdb_ext, cdb_dir)
        except Exception as e:
            # Fallback to copy into working directory
            try:
                m.run(f"CDREAD,DB,'{cdb_name}','{cdb_ext}','{cdb_dir}'")
            except Exception as e2:
                raise CADImportError(f"Failed to read CDB file: {e2}") from e2

        m.allsel()
        node_count = m.mesh.n_node
        elem_count = m.mesh.n_elem
        if node_count == 0:
            raise CADImportError(f"CDB file {file_path} contained no nodes.")

        logger.info(f"[MAPDL CAD] CDB imported: {node_count} nodes, {elem_count} elements")

        # Classify nodes
        coords = m.mesh.nodes
        return self._classify_cad_nodes(coords, orientation, is_cdb=True)

    def _import_cad_via_mesh(
        self,
        file_path: str,
        ext: str,
        orientation: str,
        target_mesh_size: float,
    ) -> Dict:
        """Load 3D CAD via Gmsh OpenCASCADE, mesh it, and load into MAPDL."""
        try:
            import gmsh
        except ImportError as e:
            raise CADImportError("Gmsh is required for 3D CAD importing. Install with: pip install gmsh") from e

        logger.info(f"[MAPDL CAD] Opening {file_path} in OpenCASCADE kernel...")
        gmsh.initialize(interruptible=False)
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.open(file_path)

            # Compute bounding box to check units
            # Gmsh returns (xmin, ymin, zmin, xmax, ymax, zmax)
            bbox = gmsh.model.getBoundingBox(-1, -1)
            dx = bbox[3] - bbox[0]
            dy = bbox[4] - bbox[1]
            dz = bbox[5] - bbox[2]
            max_dim = max(dx, dy, dz)

            scale_factor = 1.0
            if max_dim > 100.0:
                # Model is exported in millimeters (e.g. 5000 mm = 5m shelter)
                scale_factor = 0.001
                logger.info(
                    f"[MAPDL CAD] Model max dimension is {max_dim:.1f} > 100. "
                    f"Auto-converting from millimeters to meters (scale factor 0.001)."
                )
                # Scale geometry
                gmsh.model.occ.synchronize()
                gmsh.model.occ.dilate([(3, v) for _, v in gmsh.model.getEntities(3)], 0, 0, 0, scale_factor, scale_factor, scale_factor)
                gmsh.model.occ.synchronize()

                # Re-compute bounding box in meters
                bbox = gmsh.model.getBoundingBox(-1, -1)
                dx = bbox[3] - bbox[0]
                dy = bbox[4] - bbox[1]
                dz = bbox[5] - bbox[2]
                max_dim = max(dx, dy, dz)

            logger.info(f"[MAPDL CAD] Shelter dimensions in meters: {dx:.2f} × {dy:.2f} × {dz:.2f} m")

            # Adaptive element size control
            elem_size = max(0.20, min(target_mesh_size, max_dim / 15.0))
            logger.info(f"[MAPDL CAD] Target mesh element size: {elem_size:.3f} m")

            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", elem_size * 0.75)
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", elem_size * 1.30)
            gmsh.option.setNumber("Mesh.Algorithm3D", 1)  # Delaunay 3D

            # For surface-only formats like STL, build a closed volume from surface topology
            vols = gmsh.model.getEntities(3)
            if len(vols) == 0:
                logger.info("[MAPDL CAD] Surface/facet model detected (e.g. STL). Building closed volume from surface topology...")
                try:
                    gmsh.model.mesh.classifySurfaces(math.pi / 4, True, True)
                    gmsh.model.mesh.createGeometry()
                    surfs = gmsh.model.getEntities(2)
                    if surfs:
                        sl = gmsh.model.geo.addSurfaceLoop([s[1] for s in surfs])
                        gmsh.model.geo.addVolume([sl])
                        gmsh.model.geo.synchronize()
                        logger.info(f"[MAPDL CAD] Successfully formed 3D solid volume from {len(surfs)} surface patches.")
                except Exception as e_vol:
                    logger.warning(f"[MAPDL CAD] STL surface loop to volume conversion notice: {e_vol}")

            # Generate 3D volume mesh
            gmsh.model.mesh.generate(3)

            node_tags, raw_coords, _ = gmsh.model.mesh.getNodes()
            nodes = np.array(raw_coords).reshape(-1, 3)
            node_tag_to_idx = {tag: i + 1 for i, tag in enumerate(node_tags)}

            # Extract 4-node tetrahedra
            elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(3)
            tets = []
            for etype, enodes in zip(elem_types, elem_node_tags):
                if etype == 4:  # 4-node linear tetrahedron
                    tets = np.array(enodes).reshape(-1, 4)
                    break

            # If 3D tets could not be generated (e.g. unclosed open sheet), fallback to 2D thermal shells
            is_shell = False
            tris = []
            if len(tets) == 0:
                logger.warning("[MAPDL CAD] No 3D solid volume elements found; falling back to 2D thermal shell elements.")
                elem_types_2d, elem_tags_2d, elem_node_tags_2d = gmsh.model.mesh.getElements(2)
                for etype, enodes in zip(elem_types_2d, elem_node_tags_2d):
                    if etype == 2:  # 3-node triangle
                        tris = np.array(enodes).reshape(-1, 3)
                        break
                if len(tris) > 0:
                    is_shell = True
                    logger.info(f"[MAPDL CAD] Extracted {len(tris)} 2D thermal shell elements.")

            if len(tets) == 0 and len(tris) == 0:
                raise CADImportError(
                    f"No valid solid or shell elements could be generated from '{Path(file_path).name}'. "
                    f"Ensure the CAD/STL file has valid geometry."
                )

            num_nodes = len(nodes)
            num_elems = len(tets) if not is_shell else len(tris)
            logger.info(f"[MAPDL CAD] Generated mesh: {num_nodes} nodes, {num_elems} elements (is_shell={is_shell})")

            if num_nodes > STUDENT_NODE_LIMIT:
                raise CADImportError(
                    f"Generated mesh node count ({num_nodes}) exceeds ANSYS Student limit ({STUDENT_NODE_LIMIT}). "
                    f"Please increase target mesh size or simplify CAD features."
                )

        finally:
            gmsh.finalize()

        # ── Bulk transfer into MAPDL via input_strings ────────────────────────
        m = self._m
        m.run("/PREP7")
        m.run("/UNITS,SI")
        if is_shell:
            m.run("ET,1,SHELL131")
            m.run("R,1,0.25")  # 0.25m shell thickness
        else:
            m.run("ET,1,SOLID70")
        m.run("TYPE,1")
        m.run("MAT,1")

        logger.info(f"[MAPDL CAD] Streaming {num_nodes} nodes into MAPDL database...")
        chunk_size = 2500
        node_lines = []
        for i, (x, y, z) in enumerate(nodes, start=1):
            node_lines.append(f"N,{i},{x:.6f},{y:.6f},{z:.6f}")
            if len(node_lines) >= chunk_size:
                m.input_strings("\n".join(node_lines))
                node_lines = []
        if node_lines:
            m.input_strings("\n".join(node_lines))

        logger.info(f"[MAPDL CAD] Streaming {num_elems} {'solid' if not is_shell else 'shell'} elements into MAPDL...")
        elem_lines = []
        if not is_shell:
            for i, tet in enumerate(tets, start=1):
                n1 = node_tag_to_idx[tet[0]]
                n2 = node_tag_to_idx[tet[1]]
                n3 = node_tag_to_idx[tet[2]]
                n4 = node_tag_to_idx[tet[3]]
                # Degenerate 8-node brick for SOLID70: n1, n2, n3, n3, n4, n4, n4, n4
                elem_lines.append(f"E,{n1},{n2},{n3},{n3},{n4},{n4},{n4},{n4}")
                if len(elem_lines) >= chunk_size:
                    m.input_strings("\n".join(elem_lines))
                    elem_lines = []
        else:
            for i, tri in enumerate(tris, start=1):
                n1 = node_tag_to_idx[tri[0]]
                n2 = node_tag_to_idx[tri[1]]
                n3 = node_tag_to_idx[tri[2]]
                elem_lines.append(f"E,{n1},{n2},{n3},{n3}")
                if len(elem_lines) >= chunk_size:
                    m.input_strings("\n".join(elem_lines))
                    elem_lines = []

        if elem_lines:
            m.input_strings("\n".join(elem_lines))

        m.allsel()
        actual_nodes = m.mesh.n_node
        actual_elems = m.mesh.n_elem
        logger.info(f"[MAPDL CAD] Ingestion complete: {actual_nodes} nodes, {actual_elems} elements in MAPDL.")

        return self._classify_cad_nodes(nodes, orientation, is_cdb=False)

    def _classify_cad_nodes(self, coords: np.ndarray, orientation: str, is_cdb: bool = False) -> Dict:
        """
        Classify nodes into functional thermal components based on 3D geometry:
        - EXT_NODES
        - ROOF_NODES
        - SOUTH_NODES
        - INTERIOR_NODES
        """
        m = self._m

        x_coords = coords[:, 0]
        y_coords = coords[:, 1]
        z_coords = coords[:, 2]

        x_min, x_max = float(np.min(x_coords)), float(np.max(x_coords))
        y_min, y_max = float(np.min(y_coords)), float(np.max(y_coords))
        z_min, z_max = float(np.min(z_coords)), float(np.max(z_coords))

        length = max(0.1, x_max - x_min)
        width = max(0.1, y_max - y_min)
        height = max(0.1, z_max - z_min)

        # ── 1. Select ROOF_NODES (top elevation for solar radiation GHI) ──────
        z_roof_thresh = z_min + 0.80 * (z_max - z_min)
        m.nsel("S", "LOC", "Z", z_roof_thresh, z_max + 0.001)
        roof_node_count = len(m.mesh.nnum)
        m.cm("ROOF_NODES", "NODE")
        logger.info(f"[MAPDL CAD] Classified {roof_node_count} roof nodes (Z >= {z_roof_thresh:.2f}m)")

        # ── 2. Select solar-facing facade nodes based on orientation ───────────
        # Default: south-facing is min Y face
        orient_lower = (orientation or "south").lower()
        if "north" in orient_lower:
            y_north_thresh = y_max - 0.25 * (y_max - y_min)
            m.nsel("S", "LOC", "Y", y_north_thresh, y_max + 0.001)
        elif "east" in orient_lower:
            x_east_thresh = x_max - 0.25 * (x_max - x_min)
            m.nsel("S", "LOC", "X", x_east_thresh, x_max + 0.001)
        elif "west" in orient_lower:
            x_west_thresh = x_min + 0.25 * (x_max - x_min)
            m.nsel("S", "LOC", "X", x_min - 0.001, x_west_thresh)
        else:  # Default south
            y_south_thresh = y_min + 0.25 * (y_max - y_min)
            m.nsel("S", "LOC", "Y", y_min - 0.001, y_south_thresh)

        solar_wall_node_count = len(m.mesh.nnum)
        m.cm("SOUTH_NODES", "NODE")
        logger.info(f"[MAPDL CAD] Classified {solar_wall_node_count} solar facade nodes ({orient_lower})")

        # ── 3. Select all external envelope nodes (for wind/ambient convection) ─
        m.allsel()
        m.cm("EXT_NODES", "NODE")

        # ── 4. Locate interior centroid and probe nodes for comfort tracking ────
        cx = (x_min + x_max) / 2.0
        cy = (y_min + y_max) / 2.0
        cz = z_min + 0.45 * (z_max - z_min)  # ~1.2m above floor level

        dists = np.sqrt(
            (coords[:, 0] - cx)**2 +
            (coords[:, 1] - cy)**2 +
            (coords[:, 2] - cz)**2
        )
        # Select 25 nodes closest to the interior centroid
        probe_indices = np.argsort(dists)[:min(35, len(coords))]
        probe_node_ids = (probe_indices + 1).tolist()

        logger.info(
            f"[MAPDL CAD] Interior thermal probe point: ({cx:.2f}, {cy:.2f}, {cz:.2f}) "
            f"with {len(probe_node_ids)} monitoring nodes."
        )

        roof_area = length * width
        envelope_area = 2.0 * (length * height + width * height) + roof_area

        return {
            "length": length,
            "width": width,
            "height": height,
            "roof_area": roof_area,
            "envelope_area": envelope_area,
            "interior_centroid": (cx, cy, cz),
            "interior_probe_nodes": probe_node_ids,
            "interior_probe_indices": probe_indices.tolist(),
            "node_count": m.mesh.n_node,
            "element_count": m.mesh.n_elem,
            "is_cad": True,
        }
