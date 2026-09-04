# Passive Thermal Shelter Analysis & Design Recommendation Platform

A production-quality engineering application for **passive thermal shelter simulation, analysis, and optimal design recommendation**, primarily targeted at **high-altitude cold regions such as Ladakh, India**, with general support for any climatic zone.

The platform uses **PyAnsys (PyMAPDL)** to automate and communicate with a local **ANSYS Mechanical APDL (v26.1 / Student or Commercial)** installation. **ANSYS performs all actual 3D transient thermal finite-element calculations** (solid heat conduction, convection, solar heat flux, and surface radiation).

---

## 🌟 Key Features

1. **True ANSYS Finite-Element Solver Backend**:
   - Automated 3D parametric geometry modeling (walls, roof, floor, interior void).
   - Solid thermal meshing with **SOLID70** 8-node thermal elements.
   - Node count management compliant with ANSYS Student edition limitations (<128,000 nodes).
   - Real transient heat transfer solution (`ANTYPE,TRANS`, `TRNOPT,FULL`) over multi-day diurnal cycles.

2. **Real Atmospheric & Solar Boundary Conditions**:
   - Geocoding engine with high-altitude Himalayan presets (Leh, Kargil, Dras, Spiti Valley).
   - Real-time climate telemetry from the **Open-Meteo API** (Global Horizontal Solar Radiation [GHI], ambient temperature, relative humidity, wind speed).
   - Dynamic time-varying convection heat transfer coefficients using the **McAdams forced-convection correlation** ($h = 5.7 + 3.8v$).
   - Time-varying solar heat flux boundary conditions applied to roof and solar-oriented facades using MAPDL `TABLE` arrays.

3. **Multi-Design × Multi-Material Matrix Simulation**:
   - Multi-select multiple parametric shelter designs and building materials.
   - Background asynchronous execution worker with thread pool management and real-time WebSocket stage telemetry.

4. **Multi-Criteria Performance Recommendation Engine**:
   - Ranks evaluated configurations based on actual ANSYS simulation results.
   - Configurable weighted decision criteria:
     - **Comfort Compliance (35%)**: % of diurnal cycle within thermal comfort limits (e.g. 18°C–27°C).
     - **Nighttime Heat Retention (25%)**: Average overnight internal temperature.
     - **Envelope Heat Loss Minimization (20%)**.
     - **Passive Solar Gain Harvesting (15%)**.
     - **Diurnal Temperature Stability (5%)**.
   - Prominently identifies the **Recommended Configuration** with clear engineering rationale.

5. **Interactive Results Visualization**:
   - Interactive Plotly.js charts:
     - Transient indoor vs. outdoor diurnal temperature swing curves.
     - Comfort envelope bands and solar flux curves.
     - Multi-configuration comparative bar charts.
   - Sortable comparison matrix table.

6. **Automated Engineering PDF Report Generation**:
   - Multi-page PDF report export powered by **ReportLab**.
   - Includes executive summary, recommended configuration, environmental telemetry, full comparison tables, and physics assumptions.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Browser Frontend                      │
│       React 19 + TypeScript + Tailwind CSS + Plotly.js      │
│      (Studio Wizard, Live Monitor, Recommendation Dash)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP REST / WebSocket
┌──────────────────────────────▼──────────────────────────────┐
│                       FastAPI Backend                       │
│    - Location & Weather Service (Open-Meteo API)            │
│    - Material & Design Libraries (SQLite + SQLAlchemy)      │
│    - Background Simulation Worker (ThreadPoolExecutor)      │
│    - Recommendation Engine (Multi-Criteria Weighted Model)   │
│    - PDF Report Generator (ReportLab 5.0)                   │
└──────────────────────────────┬──────────────────────────────┘
                               │ PyMAPDL (gRPC)
┌──────────────────────────────▼──────────────────────────────┐
│                    ANSYS Mechanical APDL                    │
│      - 3D Geometry Generation (BLOCK, VSBV, VGLUE)          │
│      - SOLID70 Thermal Meshing (<128k nodes)                │
│      - Time-Varying BCs (TABLE Arrays: Convection, Solar)   │
│      - Full Transient Thermal Solution (ANTYPE,TRANS)       │
│      - Post-Processing & Nodal Extraction (/POST1)          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.12.3)
- **ANSYS Student or Commercial** (Installed at e.g. `D:\ANSYS\ANSYS Inc\ANSYS Student\v261`)
- **Node.js 18+** (Optional, only needed if modifying frontend source code)

### 2. Launch the Platform
Run the master startup script:
```bash
python run.py
```
Or double-click `start.bat` on Windows.

Open your browser to: **http://localhost:8000**

---

## 🧪 Running End-to-End Verification
To test the complete workflow (Database $\rightarrow$ Geocoding $\rightarrow$ Weather API $\rightarrow$ PyMAPDL $\rightarrow$ Real ANSYS Transient Solve $\rightarrow$ Recommendation Engine $\rightarrow$ PDF Report):

```bash
python scripts/verify_end_to_end.py
```

---

## 📚 Material Library (Built-in)
- **Stone Masonry**: Traditional high-density Himalayan building stone ($k=2.2$ W/mK, $\rho=2400$ kg/m³).
- **Adobe / Earth Block**: Sun-dried earth block with high thermal mass ($k=0.50$ W/mK, $\rho=1700$ kg/m³).
- **Compressed Earth Block (CEB)**: High-performance stabilized earth block ($k=0.65$ W/mK, $\rho=1900$ kg/m³).
- **Burnt Clay Brick**: Standard brick masonry ($k=0.72$ W/mK, $\rho=1700$ kg/m³).
- **Insulated Composite Wall (Stone+EPS+Stone)**: Sandwich wall system ($k=0.22$ W/mK, $\rho=1600$ kg/m³).
- **EPS / XPS / Mineral Wool Insulation**: Ultra-low conductivity thermal insulation.
- **Double Glazing**: Standard double-pane glazing ($U \approx 2.8$ W/m²K).
- **Water Thermal Mass**: Water wall / storage drums for passive solar diurnal storage ($C_p = 4186$ J/kgK).
