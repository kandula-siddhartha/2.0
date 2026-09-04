"""
PDF report generation service using ReportLab.
Generates professional engineering reports from simulation results.
"""
from __future__ import annotations

import io
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, HRFlowable, Image, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from ..config import settings

# ─── Colors ──────────────────────────────────────────────────────────────────
BRAND_BLUE = colors.HexColor("#1E3A5F")
BRAND_ACCENT = colors.HexColor("#2196F3")
BRAND_LIGHT = colors.HexColor("#E3F2FD")
TEXT_DARK = colors.HexColor("#1A1A2E")
TEXT_GRAY = colors.HexColor("#666677")
SUCCESS_GREEN = colors.HexColor("#2E7D32")
WARNING_AMBER = colors.HexColor("#F57F17")
TABLE_HEADER = colors.HexColor("#1565C0")
TABLE_ALT = colors.HexColor("#F5F9FF")
HIGHLIGHT = colors.HexColor("#FFF9C4")


def _styles() -> dict:
    """Build report paragraph styles."""
    s = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            fontSize=28,
            textColor=colors.white,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            spaceAfter=6,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            fontSize=14,
            textColor=colors.HexColor("#B3D4FF"),
            alignment=TA_CENTER,
            fontName="Helvetica",
        ),
        "h1": ParagraphStyle(
            "H1",
            fontSize=18,
            textColor=BRAND_BLUE,
            fontName="Helvetica-Bold",
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontSize=14,
            textColor=BRAND_BLUE,
            fontName="Helvetica-Bold",
            spaceBefore=8,
            spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "H3",
            fontSize=12,
            textColor=BRAND_ACCENT,
            fontName="Helvetica-Bold",
            spaceBefore=6,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body",
            fontSize=10,
            textColor=TEXT_DARK,
            fontName="Helvetica",
            leading=14,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            fontSize=8,
            textColor=TEXT_GRAY,
            fontName="Helvetica",
            leading=10,
        ),
        "note": ParagraphStyle(
            "Note",
            fontSize=9,
            textColor=TEXT_GRAY,
            fontName="Helvetica-Oblique",
            leftIndent=12,
            leading=12,
        ),
        "label": ParagraphStyle(
            "Label",
            fontSize=9,
            textColor=TEXT_GRAY,
            fontName="Helvetica-Bold",
        ),
        "value": ParagraphStyle(
            "Value",
            fontSize=10,
            textColor=TEXT_DARK,
            fontName="Helvetica",
        ),
        "rec_title": ParagraphStyle(
            "RecTitle",
            fontSize=20,
            textColor=BRAND_BLUE,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "rec_score": ParagraphStyle(
            "RecScore",
            fontSize=36,
            textColor=SUCCESS_GREEN,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
    }


def _table_style(has_highlight_row: bool = False) -> TableStyle:
    """Standard table style."""
    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ALT]),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])
    return ts


class ReportService:
    """
    Generates professional engineering PDF reports using ReportLab.
    """

    def generate_report(
        self,
        report_data: Dict,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate a PDF report.

        Parameters
        ----------
        report_data : dict
            All data needed for the report.
        output_path : str, optional
            Output file path. If None, auto-generated.

        Returns
        -------
        str: Path to the generated PDF.
        """
        if output_path is None:
            reports_dir = Path(settings.reports_dir)
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_id = str(uuid.uuid4())[:8]
            output_path = str(reports_dir / f"thermal_report_{report_id}.pdf")

        doc = BaseDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2 * cm,
        )

        # Page templates
        def header_footer(canvas, doc):
            canvas.saveState()
            w, h = A4
            # Header bar
            canvas.setFillColor(BRAND_BLUE)
            canvas.rect(0, h - 1.2 * cm, w, 1.2 * cm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawString(2 * cm, h - 0.85 * cm, "Passive Thermal Shelter Analysis")
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(w - 2 * cm, h - 0.85 * cm,
                                   report_data.get("title", "Thermal Performance Report"))
            # Footer line
            canvas.setStrokeColor(BRAND_ACCENT)
            canvas.setLineWidth(0.5)
            canvas.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)
            canvas.setFillColor(TEXT_GRAY)
            canvas.setFont("Helvetica", 7)
            canvas.drawString(2 * cm, 1.1 * cm, "CONFIDENTIAL — Engineering Analysis Document")
            canvas.drawRightString(w - 2 * cm, 1.1 * cm, f"Page {doc.page}")
            canvas.restoreState()

        frame = Frame(
            doc.leftMargin, doc.bottomMargin,
            doc.width, doc.height - 1.5 * cm,
        )
        template = PageTemplate("main", [frame], onPage=header_footer)
        doc.addPageTemplates([template])

        # Build story
        story = self._build_story(report_data)
        doc.build(story)
        return output_path

    def _build_story(self, d: Dict) -> list:
        st = _styles()
        story = []

        # ── Cover Page ────────────────────────────────────────────────────────
        story.extend(self._cover_page(d, st))
        story.append(PageBreak())

        # ── 1. Executive Summary ───────────────────────────────────────────────
        story.append(Paragraph("1. Executive Summary", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT))
        story.append(Spacer(1, 6))

        summary_text = (
            "This report presents the results of a passive thermal shelter analysis conducted "
            "using ANSYS transient thermal finite element simulation via the PyAnsys framework. "
            f"The analysis evaluated {d.get('total_combinations', '?')} shelter configurations "
            f"at {d.get('location_name', 'the specified location')} under real atmospheric conditions "
            f"retrieved from the {d.get('weather_provider', 'Open-Meteo')} API. "
            "All thermal results originate from actual ANSYS FE simulations."
        )
        story.append(Paragraph(summary_text, st["body"]))
        story.append(Spacer(1, 12))

        # ── 2. Recommended Configuration ──────────────────────────────────────
        story.append(Paragraph("2. Recommended Configuration", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT))
        story.append(Spacer(1, 6))
        story.extend(self._recommendation_section(d, st))
        story.append(Spacer(1, 12))

        # ── 3. Environmental Conditions ───────────────────────────────────────
        story.append(Paragraph("3. Environmental Conditions", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT))
        story.append(Spacer(1, 6))
        story.extend(self._environment_section(d, st))
        story.append(Spacer(1, 12))

        # ── 4. Simulation Settings ────────────────────────────────────────────
        story.append(Paragraph("4. Simulation Configuration", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT))
        story.append(Spacer(1, 6))
        story.extend(self._simulation_settings_section(d, st))
        story.append(Spacer(1, 12))

        # ── 5. Comparison Table ───────────────────────────────────────────────
        story.append(Paragraph("5. Thermal Performance Comparison", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT))
        story.append(Spacer(1, 6))
        story.extend(self._comparison_section(d, st))
        story.append(Spacer(1, 12))

        # ── 6. Assumptions & Limitations ──────────────────────────────────────
        story.append(Paragraph("6. Assumptions and Limitations", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT))
        story.append(Spacer(1, 6))
        story.extend(self._assumptions_section(d, st))
        story.append(Spacer(1, 12))

        # ── 7. Software Information ───────────────────────────────────────────
        story.append(Paragraph("7. Software and Version Information", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_ACCENT))
        story.append(Spacer(1, 6))
        story.extend(self._software_section(d, st))

        return story

    def _cover_page(self, d: Dict, st: dict) -> list:
        items = []
        items.append(Spacer(1, 3 * cm))

        # Title block
        items.append(Paragraph(d.get("title", "Passive Thermal Shelter Analysis"), st["h1"]))
        items.append(Spacer(1, 0.5 * cm))
        items.append(Paragraph("PyAnsys-Driven Thermal Performance Analysis Report", st["h2"]))
        items.append(Spacer(1, 0.3 * cm))
        items.append(HRFlowable(width="100%", thickness=2, color=BRAND_ACCENT))
        items.append(Spacer(1, 1.5 * cm))

        # Cover info table
        cover_data = [
            ["Location:", d.get("location_name", "—")],
            ["Analysis Date:", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
            ["Simulation Engine:", f"ANSYS MAPDL {d.get('ansys_version', '26.1')}"],
            ["Weather Source:", d.get("weather_provider", "Open-Meteo")],
            ["Total Configurations:", str(d.get("total_combinations", "—"))],
            ["Recommended Configuration:", d.get("recommended_label", "—")],
            ["Overall Performance Score:", f"{d.get('overall_score', 0):.1f} / 100"],
        ]
        t = Table(cover_data, colWidths=[5 * cm, 10 * cm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("TEXTCOLOR", (0, 0), (0, -1), BRAND_BLUE),
            ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDEE")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, TABLE_ALT]),
        ]))
        items.append(t)
        items.append(Spacer(1, 2 * cm))
        items.append(Paragraph(
            "Performance-based recommendation derived from ANSYS simulation results "
            "and user-defined weighting criteria. Not AI-generated.",
            st["note"],
        ))
        return items

    def _recommendation_section(self, d: Dict, st: dict) -> list:
        items = []
        rec_label = d.get("recommended_label", "—")
        score = d.get("overall_score", 0)

        items.append(Paragraph(f"Recommended Configuration: {rec_label}", st["h2"]))
        items.append(Paragraph(f"Overall Thermal Performance Score: {score:.1f} / 100", st["h3"]))
        items.append(Spacer(1, 6))

        reasons = d.get("explanation", [])
        if reasons:
            items.append(Paragraph("Reasons for Recommendation:", st["h3"]))
            for reason in reasons:
                items.append(Paragraph(f"• {reason}", st["body"]))

        return items

    def _environment_section(self, d: Dict, st: dict) -> list:
        items = []
        env = d.get("environment", {})
        env_data = [
            ["Parameter", "Value", "Source"],
            ["Location", env.get("location_name", "—"), "User Input"],
            ["Latitude", f"{env.get('latitude', '—')}°", "Geocoding API"],
            ["Longitude", f"{env.get('longitude', '—')}°", "Geocoding API"],
            ["Elevation", f"{env.get('elevation', '—')} m", "Geocoding API"],
            ["Timezone", env.get("timezone", "—"), "API"],
            ["Simulation Period", env.get("simulation_period", "—"), "User Input"],
            ["Weather Provider", d.get("weather_provider", "Open-Meteo"), "API"],
            ["Peak Solar Radiation", f"{env.get('peak_solar', '—')} W/m²", "Weather API (GHI)"],
            ["Temperature Range", f"{env.get('temp_min', '—')}°C to {env.get('temp_max', '—')}°C", "Weather API"],
            ["Wind Speed Range", f"{env.get('wind_min', '—')}–{env.get('wind_max', '—')} m/s", "Weather API"],
        ]
        t = Table(env_data, colWidths=[5.5 * cm, 6 * cm, 4 * cm])
        t.setStyle(_table_style())
        items.append(t)
        items.append(Spacer(1, 6))
        items.append(Paragraph(
            "Note: Weather data retrieved from the Open-Meteo API. GHI = Global Horizontal Irradiance. "
            "These values are API-provided and used as ANSYS boundary conditions.",
            st["note"],
        ))
        return items

    def _simulation_settings_section(self, d: Dict, st: dict) -> list:
        items = []
        sim = d.get("simulation_settings", {})
        sim_data = [
            ["Setting", "Value"],
            ["ANSYS Analysis Type", "Transient Thermal (ANTYPE,TRANS)"],
            ["Element Type", "SOLID70 (8-node thermal solid)"],
            ["Mesh Size", f"{sim.get('mesh_size', '—')} m (element edge length)"],
            ["Time Step", f"{sim.get('time_step_s', '—')} s"],
            ["Total Duration", f"{sim.get('duration_h', '—')} hours"],
            ["Convection Model", sim.get("convection_model", "McAdams correlation (wind-based)")],
            ["Solar Loading", "Enabled" if sim.get("solar_enabled", True) else "Disabled"],
            ["Radiation", "Linearized grey-body" if sim.get("radiation_enabled", True) else "Disabled"],
            ["Comfort Range", f"{sim.get('comfort_min', 18)}°C – {sim.get('comfort_max', 27)}°C"],
        ]
        t = Table(sim_data, colWidths=[7 * cm, 9 * cm])
        t.setStyle(_table_style())
        items.append(t)
        return items

    def _comparison_section(self, d: Dict, st: dict) -> list:
        items = []
        comparison = d.get("comparison_table", [])
        if not comparison:
            items.append(Paragraph("No comparison data available.", st["body"]))
            return items

        headers = ["Config", "Design", "Material", "Avg T (°C)", "Min T (°C)", "Comfort %", "Solar (kWh)", "Score"]
        rows = [headers]
        for c in comparison:
            is_rec = c.get("is_recommended", False)
            label = "★ " if is_rec else ""
            rows.append([
                label + c.get("sim_id", "")[:12],
                (c.get("design_name") or "")[:20],
                (c.get("material_name") or "")[:18],
                f"{c.get('avg_internal_temp', 0):.1f}" if c.get("avg_internal_temp") is not None else "—",
                f"{c.get('min_internal_temp', 0):.1f}" if c.get("min_internal_temp") is not None else "—",
                f"{c.get('comfort_percentage', 0):.1f}%" if c.get("comfort_percentage") is not None else "—",
                f"{c.get('total_solar_gain_kwh', 0):.2f}" if c.get("total_solar_gain_kwh") is not None else "—",
                f"{c.get('score', 0):.1f}" if c.get("score") is not None else "—",
            ])

        col_widths = [2.5 * cm, 3.5 * cm, 3.5 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.5 * cm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        ts = _table_style()
        # Highlight recommended row
        for i, c in enumerate(comparison, start=1):
            if c.get("is_recommended"):
                ts.add("BACKGROUND", (0, i), (-1, i), HIGHLIGHT)
                ts.add("FONTNAME", (0, i), (-1, i), "Helvetica-Bold")
        t.setStyle(ts)
        items.append(t)
        items.append(Spacer(1, 6))
        items.append(Paragraph("★ = Recommended Configuration | All temperature values in °C", st["note"]))
        return items

    def _assumptions_section(self, d: Dict, st: dict) -> list:
        assumptions = [
            "1. Weather data source: Open-Meteo API (ERA5/ECMWF reanalysis). Spatial resolution: ~9 km. Temporal resolution: 1 hour.",
            "2. Solar radiation values represent Global Horizontal Irradiance (GHI) — the total downward shortwave radiation on a horizontal surface.",
            "3. External convection HTC derived from the McAdams simplified flat-plate correlation: h = 5.7 + 3.8v (W/m²K), where v = wind speed (m/s). Source: McAdams (1954); ASHRAE Handbook of Fundamentals.",
            "4. Surface-to-sky radiation is represented by a linearized grey-body radiation HTC added to the convection coefficient. Full radiation view factor analysis was not performed.",
            "5. Shelter geometry is represented as a homogeneous solid shell (no internal partitions, furniture, or equipment unless configured).",
            "6. Internal air is not explicitly modeled as a fluid volume. Interior temperature is approximated from the interior solid node temperatures.",
            "7. Material properties are assumed uniform and temperature-independent.",
            "8. Solar absorptivity is applied to roof and south-facing walls only as an effective heat flux. Window solar gain through glazing is not included in this analysis version.",
            "9. Wind direction effects are not modeled; wind speed magnitude is used for HTC calculation only.",
            "10. ANSYS Student version node limit (~128,000 nodes) constrains maximum mesh density.",
        ]
        items = []
        for a in assumptions:
            items.append(Paragraph(a, st["body"]))
        return items

    def _software_section(self, d: Dict, st: dict) -> list:
        items = []
        sw_data = [
            ["Component", "Version / Detail"],
            ["ANSYS MAPDL", d.get("ansys_version", "26.1")],
            ["PyMAPDL (ansys-mapdl-core)", d.get("pymapdl_version", "0.74.1")],
            ["Python", d.get("python_version", "3.12.x")],
            ["FastAPI Backend", "0.116.1"],
            ["Weather API", "Open-Meteo (https://open-meteo.com)"],
            ["Report Generation", "ReportLab 5.0.1"],
            ["Report Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
        ]
        t = Table(sw_data, colWidths=[7 * cm, 9 * cm])
        t.setStyle(_table_style())
        items.append(t)
        return items
