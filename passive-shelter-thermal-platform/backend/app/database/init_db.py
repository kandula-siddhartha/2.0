"""
Database initialization and seeding with built-in materials and designs.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pathlib import Path

from app.config import settings
from app.database.base import Base, engine, get_db_context
from app.database.models import Material, Design, AppSetting


# ─── Built-in Material Library ───────────────────────────────────────────────
# Sources: Engineering Toolbox, ASHRAE Handbook of Fundamentals, various
# thermal engineering references. Values are representative; always verify
# against project-specific material datasheets.

BUILTIN_MATERIALS = [
    {
        "name": "Concrete (Dense)",
        "category": "structural",
        "description": "Dense reinforced concrete, common for structural walls",
        "thermal_conductivity": 1.7,    # W/m·K
        "density": 2300.0,              # kg/m³
        "specific_heat": 880.0,         # J/kg·K
        "emissivity": 0.88,
        "solar_absorptivity": 0.65,
        "solar_reflectivity": 0.35,
        "default_thickness": 0.20,
        "source": "ASHRAE Handbook of Fundamentals; Engineering Toolbox",
        "is_builtin": True,
    },
    {
        "name": "Burnt Clay Brick",
        "category": "structural",
        "description": "Standard fired clay brick, common in Himalayan region construction",
        "thermal_conductivity": 0.72,
        "density": 1700.0,
        "specific_heat": 840.0,
        "emissivity": 0.90,
        "solar_absorptivity": 0.70,
        "solar_reflectivity": 0.30,
        "default_thickness": 0.23,
        "source": "IS 3809; Engineering Toolbox",
        "is_builtin": True,
    },
    {
        "name": "Stone Masonry",
        "category": "structural",
        "description": "Local stone masonry typical of Ladakh/high-altitude region construction",
        "thermal_conductivity": 2.2,
        "density": 2400.0,
        "specific_heat": 840.0,
        "emissivity": 0.90,
        "solar_absorptivity": 0.75,
        "solar_reflectivity": 0.25,
        "default_thickness": 0.45,
        "source": "Engineering Toolbox; Himalayan construction references",
        "is_builtin": True,
    },
    {
        "name": "Adobe / Earth Block",
        "category": "structural",
        "description": "Sun-dried earth blocks; high thermal mass, traditional passive design material",
        "thermal_conductivity": 0.50,
        "density": 1700.0,
        "specific_heat": 1000.0,
        "emissivity": 0.90,
        "solar_absorptivity": 0.72,
        "solar_reflectivity": 0.28,
        "default_thickness": 0.40,
        "source": "Engineering Toolbox; Passive solar design references",
        "is_builtin": True,
    },
    {
        "name": "Timber / Wood (Softwood)",
        "category": "structural",
        "description": "Softwood timber (pine/spruce), used for framing and wall panels",
        "thermal_conductivity": 0.12,
        "density": 500.0,
        "specific_heat": 1600.0,
        "emissivity": 0.90,
        "solar_absorptivity": 0.60,
        "solar_reflectivity": 0.40,
        "default_thickness": 0.15,
        "source": "Engineering Toolbox",
        "is_builtin": True,
    },
    {
        "name": "EPS Insulation (Expanded Polystyrene)",
        "category": "insulation",
        "description": "Expanded polystyrene board insulation; very low thermal conductivity",
        "thermal_conductivity": 0.036,
        "density": 20.0,
        "specific_heat": 1500.0,
        "emissivity": 0.90,
        "solar_absorptivity": 0.30,
        "solar_reflectivity": 0.70,
        "default_thickness": 0.10,
        "source": "Engineering Toolbox; ASHRAE",
        "is_builtin": True,
    },
    {
        "name": "XPS Insulation (Extruded Polystyrene)",
        "category": "insulation",
        "description": "High-performance extruded polystyrene, better moisture resistance than EPS",
        "thermal_conductivity": 0.030,
        "density": 35.0,
        "specific_heat": 1500.0,
        "emissivity": 0.90,
        "solar_absorptivity": 0.30,
        "solar_reflectivity": 0.70,
        "default_thickness": 0.08,
        "source": "Engineering Toolbox; manufacturer data",
        "is_builtin": True,
    },
    {
        "name": "Mineral Wool / Rock Wool",
        "category": "insulation",
        "description": "Mineral/rock wool batt insulation; fire resistant, good thermal performance",
        "thermal_conductivity": 0.040,
        "density": 100.0,
        "specific_heat": 840.0,
        "emissivity": 0.90,
        "solar_absorptivity": 0.30,
        "solar_reflectivity": 0.70,
        "default_thickness": 0.10,
        "source": "Engineering Toolbox; ASHRAE",
        "is_builtin": True,
    },
    {
        "name": "Double Glazing (Air-filled)",
        "category": "glazing",
        "description": "Standard double-pane glazing with 12mm air gap; U~2.8 W/m²K",
        "thermal_conductivity": 0.10,
        "density": 2500.0,
        "specific_heat": 750.0,
        "emissivity": 0.84,
        "solar_absorptivity": 0.15,
        "solar_reflectivity": 0.15,
        "default_thickness": 0.024,
        "source": "ASHRAE; glass manufacturer data",
        "is_builtin": True,
    },
    {
        "name": "Water (Thermal Mass)",
        "category": "thermal_mass",
        "description": "Water thermal mass (e.g. water wall/drum); very high heat capacity",
        "thermal_conductivity": 0.60,
        "density": 1000.0,
        "specific_heat": 4186.0,
        "emissivity": 0.95,
        "solar_absorptivity": 0.95,
        "solar_reflectivity": 0.05,
        "default_thickness": 0.20,
        "source": "Engineering Toolbox",
        "is_builtin": True,
    },
    {
        "name": "Insulated Composite Wall (Stone+EPS+Stone)",
        "category": "composite",
        "description": "Stone-EPS-Stone sandwich wall: 150mm stone + 80mm EPS + 150mm stone. Effective k≈0.22 W/mK (approximate homogenized). Use for simple composite representation.",
        "thermal_conductivity": 0.22,
        "density": 1600.0,
        "specific_heat": 870.0,
        "emissivity": 0.90,
        "solar_absorptivity": 0.75,
        "solar_reflectivity": 0.25,
        "default_thickness": 0.38,
        "source": "Calculated from layer properties; verify against actual design",
        "is_builtin": True,
    },
    {
        "name": "Compressed Earth Block (CEB)",
        "category": "thermal_mass",
        "description": "Mechanically compressed earth block; higher density and strength than adobe",
        "thermal_conductivity": 0.65,
        "density": 1900.0,
        "specific_heat": 1050.0,
        "emissivity": 0.92,
        "solar_absorptivity": 0.73,
        "solar_reflectivity": 0.27,
        "default_thickness": 0.25,
        "source": "CRATerre publications; engineering references",
        "is_builtin": True,
    },
]


# ─── Built-in Designs ────────────────────────────────────────────────────────

BUILTIN_DESIGNS = [
    {
        "name": "Standard Residential Shelter",
        "description": "5m × 4m × 3m rectangular shelter. South-facing main wall with 1.5m² window. Moderate wall thickness. Good baseline configuration for Ladakh climate analysis.",
        "design_type": "parametric",
        "length": 5.0,
        "width": 4.0,
        "height": 3.0,
        "wall_thickness": 0.30,
        "roof_thickness": 0.25,
        "floor_thickness": 0.20,
        "floor_area": 20.0,
        "volume": 60.0,
        "window_area": 1.5,
        "door_area": 2.0,
        "window_orientation": "south",
        "glazing_u_value": 2.8,
        "orientation": "south",
        "notes": "Standard parametric design; walls/roof/floor built from APDL primitives",
        "is_builtin": True,
    },
    {
        "name": "Compact High-Insulation Shelter",
        "description": "4m × 3m × 2.8m compact shelter with thick walls (0.45m). Reduced surface area minimizes heat loss. Ideal for extreme cold conditions. Small window (0.8m²) to balance solar gain vs loss.",
        "design_type": "parametric",
        "length": 4.0,
        "width": 3.0,
        "height": 2.8,
        "wall_thickness": 0.45,
        "roof_thickness": 0.40,
        "floor_thickness": 0.25,
        "floor_area": 12.0,
        "volume": 33.6,
        "window_area": 0.8,
        "door_area": 1.8,
        "window_orientation": "south",
        "glazing_u_value": 1.5,
        "orientation": "south",
        "notes": "Thick-wall compact design for maximum insulation and minimum heat loss",
        "is_builtin": True,
    },
    {
        "name": "Solar-Optimized Trombe Shelter",
        "description": "6m × 4m × 3m shelter with large south-facing glazing area (4.0m²). Designed to maximize solar gain during the day. Thermal mass wall on south side acts as heat store.",
        "design_type": "parametric",
        "length": 6.0,
        "width": 4.0,
        "height": 3.0,
        "wall_thickness": 0.30,
        "roof_thickness": 0.25,
        "floor_thickness": 0.20,
        "floor_area": 24.0,
        "volume": 72.0,
        "window_area": 4.0,
        "door_area": 2.0,
        "window_orientation": "south",
        "glazing_u_value": 2.8,
        "orientation": "south",
        "notes": "Large glazing area for maximum passive solar gain; assess heat loss vs gain trade-off",
        "is_builtin": True,
    },
    {
        "name": "Heavy Thermal Mass Shelter",
        "description": "5m × 5m × 3m square plan with very thick walls (0.60m) for maximum thermal mass. Stabilizes diurnal temperature swings. Best for locations with high daytime solar radiation.",
        "design_type": "parametric",
        "length": 5.0,
        "width": 5.0,
        "height": 3.0,
        "wall_thickness": 0.60,
        "roof_thickness": 0.50,
        "floor_thickness": 0.30,
        "floor_area": 25.0,
        "volume": 75.0,
        "window_area": 2.0,
        "door_area": 2.0,
        "window_orientation": "south",
        "glazing_u_value": 2.0,
        "orientation": "south",
        "notes": "Maximum thermal mass configuration; slowest temperature response but best retention",
        "is_builtin": True,
    },
    {
        "name": "Alpine Passive Cabin (3D CAD STEP)",
        "description": "True 3D CAD solid model (.step) of a 5.5m × 4.2m × 3.1m high-altitude shelter with gabled pitched roof. All walls, thickness, and inner thermal cavity are geometry-integrated and solved directly in ANSYS MAPDL.",
        "design_type": "imported",
        "file_path": str(Path(settings.designs_dir) / "builtin_cad_shelter" / "alpine_shelter.step"),
        "file_format": "STEP",
        "file_size_bytes": 29468,
        "length": 5.5,
        "width": 4.2,
        "height": 3.1,
        "wall_thickness": 0.35,
        "roof_thickness": 0.30,
        "floor_thickness": 0.25,
        "floor_area": 23.1,
        "volume": 71.6,
        "orientation": "south",
        "notes": "Full 3D CAD solid model imported and solved in ANSYS MAPDL",
        "is_builtin": True,
    },
]


def init_db() -> None:
    """Create all tables and seed default data if needed."""
    Base.metadata.create_all(bind=engine)

    # Safe schema evolution for SQLite (adds contour_3d column if missing)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE simulation_results ADD COLUMN contour_3d JSON"))
            conn.commit()
    except Exception:
        pass  # Column already exists

    with get_db_context() as db:
        # Seed materials
        existing_count = db.query(Material).filter(Material.is_builtin == True).count()
        if existing_count == 0:
            for mat_data in BUILTIN_MATERIALS:
                mat = Material(**mat_data)
                db.add(mat)
            db.flush()
            print(f"[DB] Seeded {len(BUILTIN_MATERIALS)} built-in materials.")

        # Seed designs
        design_count = db.query(Design).filter(Design.is_builtin == True).count()
        if design_count == 0:
            for des_data in BUILTIN_DESIGNS:
                des = Design(**des_data)
                db.add(des)
            db.flush()
            print(f"[DB] Seeded {len(BUILTIN_DESIGNS)} built-in designs.")

        # Set app version
        ver_setting = db.query(AppSetting).filter(AppSetting.key == "db_version").first()
        if not ver_setting:
            db.add(AppSetting(key="db_version", value="1.0.0"))

    print("[DB] Database initialized successfully.")


if __name__ == "__main__":
    init_db()
