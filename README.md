# Passive Thermal Shelter Analysis & Recommendation Platform

<div align="center">

![ANSYS MAPDL](https://img.shields.io/badge/FEA%20Solver-ANSYS%20MAPDL%20v26.1%20%7C%20v24.2-005691?style=for-the-badge&logo=ansys&logoColor=white)
![PyAnsys](https://img.shields.io/badge/PyAnsys-PyMAPDL%20gRPC-FF4B4B?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React%2019-Vite%20%2B%20TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=black)


<p align="center">
  <strong>Automated 3D Transient Thermal Finite-Element Analysis, Microclimate Harvesting, and Multi-Criteria Engineering Recommendation for High-Altitude Passive Shelters</strong>
</p>

[Quick Start (1-Click)](#-1-click-universal-setup-any-windows-laptop) • [Connecting to ANSYS](#-connecting-to-ansys-on-any-laptop) • [System Architecture](#-system-architecture) • [Features](#-platform-features) • [Diagnostics](#-5-second-system-diagnostic)

</div>

---

## 📖 Project Overview

The **Passive Thermal Shelter Platform** is a research-grade engineering decision support system designed to evaluate and optimize passive building envelopes in severe high-altitude climates (such as **Leh, Ladakh, India** at 3,500m+ elevation, where winter nighttime temperatures drop below -15°C).

Unlike simplified spreadsheet models, this platform bridges **real-time climate telemetry** directly to a local **ANSYS Mechanical APDL (PyMAPDL)** finite-element solver kernel:
1. **True Transient FEA**: Discretizes shelter solids using **SOLID70** 8-node 3D thermal elements and solves transient heat diffusion (`ANTYPE,TRANS`, `TRNOPT,FULL`) over multi-day diurnal cycles.
2. **Real Atmospheric Telemetry**: Pulls hourly ambient temperatures, wind velocities, and Global Horizontal Irradiance (GHI) from the **Open-Meteo API**.
3. **Dynamic Boundary Conditions**: Applies time-varying solar radiation fluxes (`TABLE` arrays) and forced-convection film coefficients based on the **McAdams empirical correlation** ($h = 5.7 + 3.8v$).
4. **MCDA Recommendation Engine**: Automatically ranks design × material combinations using Multi-Criteria Decision Analysis across thermal comfort compliance, nocturnal heat retention, and temperature stability.
5. **Publication-Grade PDF Reporting**: Generates automated engineering PDF reports powered by ReportLab.

---

## ⚡ 1-Click Universal Setup (Any Windows Laptop)

The platform is designed to be completely portable and runnable on **any Windows laptop** with zero configuration hurdles.

> [!IMPORTANT]
> **No Node.js or npm Required on Target Laptops!**  
> The production React Single Page Application is precompiled into `passive-shelter-thermal-platform/frontend/dist/` and served statically by FastAPI. You **only need Python 3.10+ installed** to run the complete interactive platform.

### Step 1: Clone the Repository
```bash
git clone https://github.com/kandula-siddhartha/2.0.git
cd 2.0
```

### Step 2: Double-Click the 1-Click Launcher
Simply double-click **`setup_and_run.bat`** (or run it from PowerShell/CMD):
```cmd
setup_and_run.bat
```

**What the automated launcher does:**
1. Verifies that Python 3.10+ is installed on your system.
2. Automatically creates a local isolated virtual environment (`.venv`).
3. Automatically installs/verifies all required packages from `backend/requirements.txt`.
4. Runs automated system diagnostics and scans for your local ANSYS MAPDL installation.
5. Automatically initializes the SQLite database and seeds 9 thermal materials and 5 baseline blueprints.
6. Launches the server and opens your web browser to **`http://localhost:8000`**.

---

## 🔌 Connecting to ANSYS on Any Laptop

The platform communicates with ANSYS Mechanical APDL via PyMAPDL gRPC. It supports both **ANSYS Student (Free Academic)** and **Commercial / Research licenses** (v2022 to v2026).

```
   ┌──────────────────────┐             ┌──────────────────────┐
   │  Web Studio UI       │  REST / WS  │  FastAPI Backend     │
   │  (React 19 + Plotly) ├────────────►│  (Python 3.10+)      │
   └──────────────────────┘             └──────────┬───────────┘
                                                   │ PyMAPDL (gRPC)
                                        ┌──────────▼───────────┐
                                        │ ANSYS MAPDL Kernel   │
                                        │ SOLID70 3D FEA Solve │
                                        └──────────────────────┘
```

### Automatic Multi-Drive Discovery
On startup, the platform automatically searches for ANSYS across:
- **Environment variables**: `AWP_ROOT261`, `AWP_ROOT252`, `AWP_ROOT251`, `AWP_ROOT242`, `AWP_ROOT232`, `AWP_ROOT222`, `ANSYS_ROOT`
- **Standard drive locations**:
  - `C:\Program Files\ANSYS Inc\v242\` or `v261\`
  - `C:\Program Files\ANSYS Inc\ANSYS Student\v242\` or `v261\`
  - `D:\ANSYS\ANSYS Inc\ANSYS Student\v261\`
  - `D:\Program Files\ANSYS Inc\...`

### In-App "Connect to ANSYS" UI & Wizard
If your ANSYS installation is located in a custom directory:
1. Click the **ANSYS MAPDL status badge** in the top navigation bar, or open **ANSYS Setup** (`/settings`).
2. In the **"Connect ANSYS Installation"** card, paste your `ansysXXX.exe` or installation root directory (e.g. `C:\Program Files\ANSYS Inc\v242\ansys\bin\winx64\ansys242.exe`).
3. Click **Auto-Detect** or **Save & Connect**.
4. Click **Test Live Connection** to verify live gRPC communication with the MAPDL solver.

> [!NOTE]
> **Strict ANSYS Policy**:  
> Simulations strictly solve inside the real local ANSYS Mechanical APDL finite-element kernel (`ANTYPE,TRANS`). If ANSYS is not connected, the platform will prompt you to connect ANSYS before running simulations.

---

## 🔍 5-Second System Diagnostic

You can verify your environment, Python libraries, database, and ANSYS solver readiness at any time:

```bash
python passive-shelter-thermal-platform/scripts/verify_setup.py
```

**Expected Diagnostic Output:**
```text
========================================================================
  PASSIVE THERMAL SHELTER PLATFORM — ENVIRONMENT & SOLVER DIAGNOSTIC
========================================================================

[1/5] Python Environment:
  [PASS] Python 3.12.3 (compatible >= 3.10)

[2/5] Python Package Dependencies:
  [PASS] FastAPI, Uvicorn, SQLAlchemy, Pydantic, NumPy, Pandas, Plotly, ReportLab, PyMAPDL

[3/5] SQLite Database & Seed Data:
  [PASS] Database initialized successfully. Materials loaded: 9 | Designs loaded: 5

[4/5] ANSYS MAPDL Solver Kernel:
  [PASS] ANSYS MAPDL v26.1 Verified on Disk
         License Tier:   ANSYS Student (<128k nodes)
         Executable:     D:\ANSYS\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ansys261.exe

[5/5] Compiled Frontend Production UI:
  [PASS] Precompiled React UI exists at: .../frontend/dist/index.html
         (No Node.js or npm required on target laptop!)

========================================================================
  ALL CORE CHECKS PASSED: Platform is fully ready to run ANSYS FEA!
========================================================================
```

---

## 🌟 Platform Features

### 1. Simulation Studio (5-Step Wizard)
- **Step 1: Microclimate & Geography**: Pre-configured high-altitude presets (Leh, Dras, Kargil, Spiti) or global search with live Open-Meteo hourly weather telemetry.
- **Step 2: Blueprint & Material Matrix**: Multi-select parametric shelter geometries and specialized thermal materials.
- **Step 3: Facade Orientation**: Cardinal & sub-cardinal bearings (`South`, `Southeast`, `Southwest`, `East`, `West`, `North`) with corresponding solar radiation curves.
- **Step 4: Thermal Physics & Meshing**: Configurable SOLID70 mesh sizing (0.35m tuned for ANSYS Student <128,000 node constraints), surface radiation, and McAdams convection.
- **Step 5: Review & Launch**: Review matrix combinations and launch asynchronous solver queue.

### 2. Calibrated Material Library
- **Stone Masonry**: $k = 2.20$ W/m·K, $\rho = 2400$ kg/m³, $c_p = 840$ J/kg·K (high thermal mass)
- **Adobe / Sun-Dried Earth**: $k = 0.50$ W/m·K, $\rho = 1700$ kg/m³, $c_p = 1000$ J/kg·K
- **Compressed Stabilized Earth Block (CSEB)**: $k = 0.65$ W/m·K, $\rho = 1900$ kg/m³
- **Burnt Clay Brick**: $k = 0.72$ W/m·K, $\rho = 1700$ kg/m³
- **Sandwich Wall (Stone + EPS Insulation + Stone)**: $k = 0.22$ W/m·K, $\rho = 1600$ kg/m³
- **EPS / XPS / Mineral Wool Insulation**: Ultra-low conductivity thermal insulation ($k = 0.035$ W/m·K)
- **Double Glazing**: $U \approx 2.8$ W/m²·K with selective solar heat gain

### 3. Live ANSYS Solver Monitor
- Real-time WebSocket streaming showing active job progress, APDL stage updates (`BUILDING_GEOMETRY`, `MESHING_SOLID70`, `APPLYING_BCS`, `SOLVING`, `EXTRACTING_RESULTS`), and console telemetry.

### 4. Recommendation Dashboard & MCDA Scoring
- Multi-Criteria Decision Analysis (MCDA) model scoring each configuration:
  $$\text{Score} = w_1 \cdot C_{\text{comfort}} + w_2 \cdot R_{\text{night}} + w_3 \cdot (1 - L_{\text{loss}}) + w_4 \cdot S_{\text{solar}} + w_5 \cdot T_{\text{stability}}$$
- Displays Rank #1 Winner Card with full location coordinates, elevation, evaluated date period, and comparative interactive charts.

### 5. Automated PDF Engineering Reports
- Downloadable multi-page reports generated with **ReportLab**, including executive summary, weather telemetry graphs, comparative bar charts, and ANSYS physics solver configurations.

---

## 📁 Repository Structure

```
2.0/
├── setup_and_run.bat                # 1-Click universal launcher for any Windows laptop
├── start.bat                        # Fast launcher using existing .venv
├── run.py                           # Master Python server launcher
├── package.json                     # Root npm script shortcuts (optional)
├── README.md                        # Project documentation (this file)
└── passive-shelter-thermal-platform/
    ├── setup_and_run.bat            # Inner launcher script
    ├── start.bat                    # Inner fast start script
    ├── run.py                       # Platform launcher
    ├── backend/
    │   ├── requirements.txt         # Python dependencies (FastAPI, PyMAPDL, etc.)
    │   └── app/
    │       ├── main.py              # FastAPI application entry & SPA static server
    │       ├── config.py            # Dynamic settings & ANSYS path persistence
    │       ├── api/                 # REST API routers (ansys, simulations, designs, etc.)
    │       ├── database/            # SQLAlchemy models & database seeder
    │       ├── mapdl_integration/   # ANSYS MAPDL integration (session, meshing, solver)
    │       ├── services/            # Weather (Open-Meteo), Geocoding, MCDA Recommendation
    │       └── worker/              # Background simulation job queue worker
    ├── frontend/
    │   ├── dist/                    # Precompiled production React bundle (zero-node execution)
    │   ├── src/                     # React 19 + TypeScript source code
    │   │   ├── pages/               # Studio, Dashboard, Live Monitor, Material Library, Settings
    │   │   ├── components/          # TopHeader, Sidebar, Navigation
    │   │   └── api.ts               # Axios API client
    │   └── vite.config.ts           # Vite build configuration
    ├── data/
    │   ├── shelter_thermal.db       # SQLite database (materials, designs, simulations)
    │   ├── designs/                 # CAD geometry storage (.step, .iges, .cdb, .stl)
    │   ├── reports/                 # Generated ReportLab PDF reports
    │   └── simulations/             # Transient FEA job run scratch storage
    └── scripts/
        ├── verify_setup.py          # 5-second environment diagnostic script
        └── verify_end_to_end.py     # Full end-to-end simulation verification script
```

---

## 💻 Developer Guide (Hot-Reload Mode)

If you are developing or modifying the React frontend source code, you can run the backend and Vite dev server simultaneously:

### Terminal 1: Backend
```bash
python run.py
```

### Terminal 2: Frontend (with Hot-Module Reloading)
```bash
cd passive-shelter-thermal-platform/frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** for hot-reloading development.

To recompile the production bundle for portable single-click deployment:
```bash
npm run build
```

---

## 📜 Full End-to-End Verification

To execute a complete automated test verifying the entire pipeline (Database $\rightarrow$ Geocoding $\rightarrow$ Weather API $\rightarrow$ PyMAPDL $\rightarrow$ Real ANSYS Transient Thermal FEA Solve $\rightarrow$ Recommendation Engine $\rightarrow$ ReportLab PDF):

```bash
python passive-shelter-thermal-platform/scripts/verify_end_to_end.py
```

---

## 📄 License & Attribution
Developed for high-altitude passive solar architecture research and engineering thermal optimization using **ANSYS Mechanical APDL** and **PyAnsys**.
