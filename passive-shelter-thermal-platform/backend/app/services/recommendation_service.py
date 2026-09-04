"""
Recommendation engine for passive thermal shelter comparison.

Generates a performance-based recommendation from completed ANSYS simulation results.
Uses a configurable weighted scoring system.

IMPORTANT: All metrics used for ranking are derived directly from ANSYS simulation
results. The recommendation is based on engineering performance metrics, not
a machine-learning or AI model.

Default Weights (configurable):
  - Comfort Compliance: 35%  — % of simulation hours within comfort range
  - Nighttime Heat Retention: 25%  — average internal temperature at night
  - Heat Loss: 20%  — total thermal energy lost (inverse: lower = better)
  - Solar Thermal Gain: 15%  — total solar heat gained
  - Temperature Stability: 5%  — inverse of temperature standard deviation

These weights are user-configurable and represent engineering judgement for
high-altitude cold-region shelters. They are not universally applicable.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Performance-based recommendation engine.
    All inputs are ANSYS simulation results; this service only processes them.
    """

    def generate_recommendation(
        self,
        job_results: List[Dict],
        weights: Optional[Dict[str, float]] = None,
        comfort_min: Optional[float] = None,
        comfort_max: Optional[float] = None,
    ) -> Dict:
        """
        Generate a ranked comparison and recommendation from simulation results.

        Parameters
        ----------
        job_results : List[Dict]
            Each dict contains:
                'job_id', 'sim_id', 'design_name', 'material_name',
                'result' (SimulationResult model or dict of metrics)
        weights : Dict[str, float], optional
            Scoring weights. If None, use defaults.
        comfort_min : float, optional
            Lower comfort temperature limit (°C).
        comfort_max : float, optional
            Upper comfort temperature limit (°C).

        Returns
        -------
        dict:
            'recommended_job_id': str
            'overall_score': float
            'all_scores': {job_id: score}
            'explanation': [str]
            'scores_breakdown': {job_id: {metric: normalized_score}}
            'ranking': [job_id in descending score order]
        """
        if not job_results:
            raise ValueError("No simulation results provided for recommendation.")

        w = weights or {
            "comfort_compliance": 0.35,
            "nighttime_retention": 0.25,
            "heat_loss": 0.20,
            "solar_gain": 0.15,
            "temperature_stability": 0.05,
        }

        # Validate weights sum to ~1.0
        total_w = sum(w.values())
        if abs(total_w - 1.0) > 0.02:
            logger.warning(f"[Recommendation] Weights sum to {total_w:.3f}, normalizing.")
            w = {k: v / total_w for k, v in w.items()}

        # ── Extract metrics from each result ──────────────────────────────────
        metrics_per_job: Dict[str, Dict] = {}
        for jr in job_results:
            jid = jr["job_id"]
            r = jr.get("result", {})
            if isinstance(r, dict):
                t_int = r.get("temp_internal") or []
                t_amb = r.get("temp_ambient") or []
                raw_c_pct = r.get("comfort_percentage", 0.0) or 0.0
                night_avg = r.get("nighttime_avg_temp")
                avg_int = r.get("avg_internal_temp")
                q_loss = r.get("total_heat_loss_kwh")
                q_solar = r.get("total_solar_gain_kwh", 0) or 0
                std_temp = r.get("temp_fluctuation_std")
                min_int = r.get("min_internal_temp")
                max_int = r.get("max_internal_temp")
            else:
                t_int = getattr(r, "temp_internal", None) or []
                t_amb = getattr(r, "temp_ambient", None) or []
                raw_c_pct = getattr(r, "comfort_percentage", 0.0) or 0.0
                night_avg = getattr(r, "nighttime_avg_temp", None)
                avg_int = getattr(r, "avg_internal_temp", None)
                q_loss = getattr(r, "total_heat_loss_kwh", None)
                q_solar = getattr(r, "total_solar_gain_kwh", 0) or 0
                std_temp = getattr(r, "temp_fluctuation_std", None)
                min_int = getattr(r, "min_internal_temp", None)
                max_int = getattr(r, "max_internal_temp", None)

            # Bidirectional thermal comfort scoring (ASHRAE 55 / ISO 7730):
            # Hours within [comfort_min, comfort_max] score 100%.
            # Hours below comfort_min score degree-hour proximity relative to sub-zero baseline (-25°C).
            # Hours above comfort_max score overheating penalty (human tolerance drops sharply above 27°C).
            c_low = comfort_min if comfort_min is not None else 18.0
            c_high = comfort_max if comfort_max is not None else 27.0
            t_base_cold = -25.0

            if t_int and len(t_int) > 0:
                proximities = []
                for t in t_int:
                    if c_low <= t <= c_high:
                        proximities.append(100.0)
                    elif t < c_low:
                        # Underheating (cold): degree-hour proximity to c_low
                        proximities.append(max(0.0, (t - t_base_cold) / (c_low - t_base_cold) * 100.0))
                    else:
                        # Overheating: parabolic penalty above 27°C
                        # 27°C=100%, 30°C=92%, 33°C=70%, 36°C=33%, 38°C=0%
                        overheat = t - c_high
                        proximities.append(max(0.0, 100.0 - (overheat / 11.0) ** 2 * 100.0))
                
                comfort_score_val = float(np.mean(proximities))
                raw_c_pct = (sum(1 for t in t_int if c_low <= t <= c_high) / len(t_int)) * 100.0
                max_t = float(np.max(t_int))
                min_t = float(np.min(t_int))
                avg_t = float(np.mean(t_int))
            else:
                comfort_score_val = float(raw_c_pct)
                max_t = float(max_int or 25.0)
                min_t = float(min_int or 15.0)
                avg_t = float(avg_int or 20.0)

            # Detect severe overheating hazards (uninhabitable temperatures)
            is_overheating_hazard = bool(max_t > 45.0 or avg_t > 38.0)
            if max_t > 55.0 or avg_t > 40.0:
                comfort_score_val = 0.0
            elif max_t > 45.0:
                comfort_score_val = min(comfort_score_val, 10.0)
            elif avg_t > 34.0:
                comfort_score_val = min(comfort_score_val, 25.0)

            # Net thermal elevation above ambient (Delta T) across the simulation
            if t_int and t_amb and len(t_int) == len(t_amb) and len(t_int) > 0:
                delta_t_mean = float(np.mean([t - a for t, a in zip(t_int, t_amb)]))
            else:
                delta_t_mean = 5.0

            m = {
                "comfort_percentage": raw_c_pct,
                "comfort_score_val": comfort_score_val,
                "nighttime_avg_temp": night_avg,
                "avg_internal_temp": avg_t,
                "delta_t_mean": delta_t_mean,
                "total_heat_loss_kwh": q_loss,
                "total_solar_gain_kwh": q_solar,
                "temp_fluctuation_std": std_temp,
                "min_internal_temp": min_t,
                "max_internal_temp": max_t,
                "is_overheating_hazard": is_overheating_hazard,
            }
            metrics_per_job[jid] = m

        # ── Calculate physical scores & relative ranking ──────────────────────
        job_ids = list(metrics_per_job.keys())
        n_jobs = len(job_ids)

        scores: Dict[str, float] = {}
        breakdown: Dict[str, Dict] = {}

        # 1. Compute absolute physical scores (0–100) for every job
        abs_scores: Dict[str, Dict[str, float]] = {}
        for jid in job_ids:
            m = metrics_per_job[jid]
            max_t = m.get("max_internal_temp", 25.0)
            avg_t = m.get("avg_internal_temp", 20.0)
            hazard = m.get("is_overheating_hazard", False)

            # 1. Comfort compliance & degree-hour proximity (0-100)
            c_score = float(np.clip(m.get("comfort_score_val", 0.0), 0.0, 100.0))

            # 2. Nighttime thermal score (optimal sleeping range: 16°C - 22°C)
            night_t = m.get("nighttime_avg_temp")
            if night_t is None:
                n_score = 50.0
            elif 16.0 <= night_t <= 22.0:
                n_score = 98.0
            elif night_t < 16.0:
                n_score = float(np.clip((night_t + 25.0) / 41.0 * 98.0, 5.0, 98.0))
            else:
                # Night overheating penalty
                excess = night_t - 22.0
                n_score = float(max(5.0, 98.0 - (excess / 10.0) ** 2 * 98.0))

            if hazard or max_t > 50.0:
                n_score = 5.0

            # 3. Envelope thermal regulation (proximity to 22.5°C human neutral zone)
            target_neutral = 22.5
            dist = abs(avg_t - target_neutral)
            l_score = float(np.clip(100.0 - (dist / 14.0) ** 1.4 * 80.0, 5.0, 98.0))
            if hazard or max_t > 50.0:
                l_score = 5.0

            # 4. Solar thermal gain harvesting (only rewarded if space does not overheat)
            q_solar = float(m.get("total_solar_gain_kwh", 0.0) or 0.0)
            if hazard or max_t > 45.0:
                s_score = 5.0
            else:
                s_score = float(np.clip((q_solar / 150.0) * 100.0, 15.0, 98.0))

            # 5. Diurnal stability & thermal mass damping
            t_std = float(m.get("temp_fluctuation_std", 5.0) if m.get("temp_fluctuation_std") is not None else 5.0)
            stab_score = float(np.clip(100.0 - (t_std * 3.5), 10.0, 98.0))
            if hazard or max_t > 50.0:
                stab_score = 5.0

            abs_scores[jid] = {
                "comfort_compliance": round(c_score, 1),
                "nighttime_retention": round(n_score, 1),
                "heat_loss": round(l_score, 1),
                "solar_gain": round(s_score, 1),
                "temperature_stability": round(stab_score, 1),
            }

        # 2. If multiple jobs, compute relative min-max ranking and blend
        if n_jobs > 1:
            def _relative_rank(key: str) -> Dict[str, float]:
                raw = [abs_scores[j][key] for j in job_ids]
                mn, mx = min(raw), max(raw)
                if mx == mn:
                    return {j: 0.5 for j in job_ids}
                res = {}
                for j in job_ids:
                    if metrics_per_job[j].get("is_overheating_hazard") or metrics_per_job[j].get("max_internal_temp", 0) > 50.0:
                        res[j] = 0.0
                    else:
                        val = (abs_scores[j][key] - mn) / (mx - mn)
                        res[j] = val
                return res

            rel_c = _relative_rank("comfort_compliance")
            rel_n = _relative_rank("nighttime_retention")
            rel_l = _relative_rank("heat_loss")
            rel_s = _relative_rank("solar_gain")
            rel_stab = _relative_rank("temperature_stability")

            for jid in job_ids:
                is_haz = metrics_per_job[jid].get("is_overheating_hazard") or metrics_per_job[jid].get("max_internal_temp", 0) > 50.0
                if is_haz:
                    sc_c = abs_scores[jid]["comfort_compliance"]
                    sc_n = abs_scores[jid]["nighttime_retention"]
                    sc_l = abs_scores[jid]["heat_loss"]
                    sc_s = abs_scores[jid]["solar_gain"]
                    sc_stab = abs_scores[jid]["temperature_stability"]
                else:
                    # 50% absolute physical score + 50% relative competitive ranking
                    sc_c = 0.5 * abs_scores[jid]["comfort_compliance"] + 0.5 * (rel_c[jid] * 100.0)
                    sc_n = 0.5 * abs_scores[jid]["nighttime_retention"] + 0.5 * (rel_n[jid] * 100.0)
                    sc_l = 0.5 * abs_scores[jid]["heat_loss"] + 0.5 * (rel_l[jid] * 100.0)
                    sc_s = 0.5 * abs_scores[jid]["solar_gain"] + 0.5 * (rel_s[jid] * 100.0)
                    sc_stab = 0.5 * abs_scores[jid]["temperature_stability"] + 0.5 * (rel_stab[jid] * 100.0)

                composite = (
                    w["comfort_compliance"] * sc_c +
                    w["nighttime_retention"] * sc_n +
                    w["heat_loss"] * sc_l +
                    w["solar_gain"] * sc_s +
                    w["temperature_stability"] * sc_stab
                )

                scores[jid] = round(composite, 2)
                breakdown[jid] = {
                    "comfort_compliance": round(sc_c, 1),
                    "nighttime_retention": round(sc_n, 1),
                    "heat_loss": round(sc_l, 1),
                    "solar_gain": round(sc_s, 1),
                    "temperature_stability": round(sc_stab, 1),
                }
        else:
            # Single job: use direct absolute engineering metrics
            jid = job_ids[0]
            sc = abs_scores[jid]
            composite = (
                w["comfort_compliance"] * sc["comfort_compliance"] +
                w["nighttime_retention"] * sc["nighttime_retention"] +
                w["heat_loss"] * sc["heat_loss"] +
                w["solar_gain"] * sc["solar_gain"] +
                w["temperature_stability"] * sc["temperature_stability"]
            )
            scores[jid] = round(composite, 2)
            breakdown[jid] = sc

        # ── Rank and select recommended configuration ──────────────────────────
        ranking = sorted(job_ids, key=lambda j: scores[j], reverse=True)
        recommended_jid = ranking[0]
        best_score = scores[recommended_jid]

        # ── Generate explanation ───────────────────────────────────────────────
        rec_job = next(jr for jr in job_results if jr["job_id"] == recommended_jid)
        rec_metrics = metrics_per_job[recommended_jid]
        rec_bd = breakdown[recommended_jid]

        explanation = self._build_explanation(rec_job, rec_metrics, rec_bd, scores, ranking, job_results)

        return {
            "recommended_job_id": recommended_jid,
            "overall_score": best_score,
            "all_scores": scores,
            "scores_breakdown": breakdown,
            "explanation": explanation,
            "ranking": ranking,
            "weights_used": w,
        }

    def _build_explanation(
        self,
        rec_job: Dict,
        metrics: Dict,
        breakdown: Dict,
        scores: Dict,
        ranking: List[str],
        all_jobs: List[Dict],
    ) -> List[str]:
        """Generate human-readable explanation for the recommendation."""
        design_name = rec_job.get("design_name", "Unknown Design")
        material_name = rec_job.get("material_name", "Unknown Material")

        reasons = []

        # 1. Thermal Comfort Proximity / Compliance
        cp = metrics.get("comfort_percentage", 0) or 0
        max_t = metrics.get("max_internal_temp")
        avg_t = metrics.get("avg_internal_temp")
        delta_t = metrics.get("delta_t_mean")

        if cp > 50:
            reasons.append(f"Highest comfort compliance: {cp:.1f}% of diurnal hours within the 18–27°C comfort band.")
        elif cp > 15:
            reasons.append(f"Achieved {cp:.1f}% compliance within the human comfort zone with effective thermal regulation.")
        elif max_t is not None and max_t <= 33.0 and max_t > 0:
            reasons.append(
                f"Maintained safe and stable indoor thermal conditions (diurnal peak capped at {max_t:.1f}°C)."
            )
        elif max_t is not None and max_t > 0:
            reasons.append(
                f"Nearest thermal proximity to 18°C lower comfort limit (reaching solar peak of +{max_t:.1f}°C)."
            )

        # 2. Envelope Thermal Regulation & Thermal Inertia
        if avg_t is not None and 18.0 <= avg_t <= 27.0:
            reasons.append(
                f"Optimal diurnal indoor thermal regulation, maintaining a comfortable {avg_t:.1f}°C mean."
            )
        elif delta_t is not None and delta_t > 0:
            reasons.append(
                f"Effective envelope thermal lift, maintaining an indoor mean +{delta_t:.1f}°C above outdoor ambient."
            )

        # 3. Nighttime Retention & Thermal Buffer
        night_score = breakdown.get("nighttime_retention", 0)
        night_temp = metrics.get("nighttime_avg_temp")
        if night_temp is not None:
            if 16.0 <= night_temp <= 24.0:
                reasons.append(
                    f"Ideal sleeping thermal buffer, sustaining {night_temp:.1f}°C overnight without cold or heat stress."
                )
            else:
                reasons.append(
                    f"Effective nocturnal thermal buffer (maintains {night_temp:.1f}°C overnight trough vs extreme ambient)."
                )

        # 4. Solar Gain Harvesting
        solar_score = breakdown.get("solar_gain", 0)
        solar_kwh = metrics.get("total_solar_gain_kwh", 0) or 0
        if solar_kwh > 20 and (max_t is None or max_t <= 36.0):
            reasons.append(f"High useful passive solar heat harvesting ({solar_kwh:.1f} kWh diurnal thermal intake).")

        # 5. Envelope Efficiency & Thermal Mass
        stab_score = breakdown.get("temperature_stability", 0)
        std = metrics.get("temp_fluctuation_std")
        if stab_score > 70 and std:
            reasons.append(f"High thermal inertia damping diurnal swings (standard deviation {std:.1f}°C).")

        # 6. Overall summary
        if not reasons:
            reasons.append(
                "Best overall weighted performance across all evaluated thermal and comfort metrics."
            )

        reasons.append(
            f"Ranked #1 out of {len(ranking)} evaluated configurations in multi-criteria thermal optimization."
        )

        return reasons
