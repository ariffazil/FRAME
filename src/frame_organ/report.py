"""
FRAME — Chamber 6: REPORT
Daily/weekly institutional health brief. Sealed to VAULT999.
"""

import time
from typing import Optional

from pydantic import BaseModel

from .baseline import get_baseline, get_federation_baseline
from .probe import FederationProbe
from .compare import DriftReport
from .trend import get_federation_trend, TrendSeries


class InstitutionalReport(BaseModel):
    report_id: str
    timestamp: str
    period: str  # "daily" | "weekly"
    federation_health: dict
    organ_status: dict
    drift_summary: dict
    trend: dict
    constitutional_health: dict
    recommendations: list[str]
    delta_s_estimate: float = 0.0
    seal_ready: bool = False


def generate_report(
    probe: Optional[FederationProbe] = None,
    drift: Optional[DriftReport] = None,
    trend: Optional[TrendSeries] = None,
    period: str = "daily",
) -> InstitutionalReport:
    """Generate an institutional health report."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report_id = f"frame-{period}-{time.strftime('%Y%m%d-%H%M')}"

    baseline = get_baseline()
    fed_baseline = get_federation_baseline()

    # Organ status summary
    organ_status = {}
    if probe:
        for o in probe.organs:
            organ_status[o.organ] = {
                "healthy": o.healthy,
                "latency_ms": o.latency_ms,
                "status": o.status,
            }

    # Federation health
    federation_health = {
        "organs_up": probe.healthy_organs if probe else "unknown",
        "organs_total": probe.total_organs if probe else len(baseline.get("organs", {})),
        "fq": probe.fq.get("quotient") if probe and probe.fq else "unknown",
        "fq_verdict": probe.fq.get("verdict") if probe and probe.fq else "unknown",
        "probe_duration_ms": probe.probe_duration_ms if probe else 0,
    }

    # Drift summary
    drift_summary = {
        "total_drifts": drift.total_drifts if drift else 0,
        "verdict": drift.overall_verdict if drift else "UNKNOWN",
        "critical_count": sum(1 for s in drift.signals if s.severity == "CRITICAL") if drift else 0,
    }

    # Trend
    trend_data = {
        "direction": trend.direction if trend else "UNKNOWN",
        "slope_per_hour": trend.slope if trend else 0,
        "data_points": len(trend.points) if trend else 0,
    }

    # Constitutional health
    floors = baseline.get("floors", {})
    constitutional_health = {
        "f1_violations": floors.get("f1_amanah", {}).get("violations", 0),
        "f2_epistemic_accuracy": floors.get("f2_truth", {}).get("epistemic_accuracy", 0.9),
        "f4_avg_delta_s": floors.get("f4_clarity", {}).get("avg_delta_s", 0.0),
        "f8_avg_g_score": floors.get("f8_genius", {}).get("avg_g_score", 0.8),
    }

    # Recommendations
    recommendations = []
    if drift and drift.overall_verdict in ("CRITICAL", "DEGRADING"):
        recommendations.append("Investigate drift sources and schedule organ maintenance")
    if probe and probe.fq and isinstance(probe.fq, dict):
        fq_val = probe.fq.get("quotient", 1.0)
        if fq_val < 0.5:
            recommendations.append(
                "FQ CRITICAL — pause non-essential mutation, prioritize verification"
            )
        elif fq_val < 0.7:
            recommendations.append("FQ WARNING — increase verify-to-execute ratio")
    if trend and trend.direction == "DECAYING":
        recommendations.append("Federation trend is DECAYING — review RSI effectiveness")
    if not recommendations:
        recommendations.append("No immediate action required — federation is STABLE")

    # Delta S estimate
    ds = 0.0
    if drift:
        ds += drift.total_drifts * 0.05
    if trend and trend.direction == "DECAYING":
        ds += 0.1
    if trend and trend.direction == "IMPROVING":
        ds -= 0.1

    return InstitutionalReport(
        report_id=report_id,
        timestamp=ts,
        period=period,
        federation_health=federation_health,
        organ_status=organ_status,
        drift_summary=drift_summary,
        trend=trend_data,
        constitutional_health=constitutional_health,
        recommendations=recommendations,
        delta_s_estimate=round(ds, 3),
        seal_ready=drift is not None and drift.overall_verdict == "STABLE",
    )
