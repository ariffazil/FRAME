"""
FRAME — Chamber 3: COMPARE
Diff current probe results against baseline. Compute drift vectors.
"""

import time
from typing import Optional

from pydantic import BaseModel

from .baseline import get_baseline, get_organ_baseline
from .probe import FederationProbe, OrganProbe


class DriftSignal(BaseModel):
    organ: str
    metric: str
    baseline_value: str
    current_value: str
    drift_delta: str
    severity: str  # "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    trend: str = "STABLE"  # "IMPROVING" | "STABLE" | "DECAYING"


class DriftReport(BaseModel):
    timestamp: str
    total_drifts: int
    signals: list[DriftSignal]
    overall_verdict: str  # "STABLE" | "DRIFTING" | "DEGRADING" | "CRITICAL"


def compare_organ(probe: OrganProbe) -> list[DriftSignal]:
    """Compare a single organ probe against its baseline."""
    signals = []
    baseline = get_organ_baseline(probe.organ)

    if not baseline:
        return signals

    # Health drift
    bl_health = baseline.get("health", "healthy")
    if probe.status in ("down", "error") and bl_health == "healthy":
        signals.append(
            DriftSignal(
                organ=probe.organ,
                metric="health",
                baseline_value=bl_health,
                current_value=probe.status,
                drift_delta="DOWN",
                severity="CRITICAL",
                trend="DECAYING",
            )
        )

    # Latency drift
    bl_lat = baseline.get("latency_ms", 0)
    if bl_lat > 0 and probe.latency_ms > bl_lat * 3:
        signals.append(
            DriftSignal(
                organ=probe.organ,
                metric="latency_ms",
                baseline_value=str(bl_lat),
                current_value=str(probe.latency_ms),
                drift_delta=f"+{probe.latency_ms - bl_lat:.0f}ms",
                severity="HIGH",
                trend="DECAYING",
            )
        )

    return signals


def compare_federation(probe: FederationProbe) -> DriftReport:
    """Compare full federation probe against all baselines."""
    all_signals = []

    for organ_probe in probe.organs:
        signals = compare_organ(organ_probe)
        all_signals.extend(signals)

    # FQ drift
    bl = get_baseline()
    bl_fq = bl.get("federation", {}).get("avg_fq", 1.0)
    if probe.fq and isinstance(probe.fq, dict):
        current_fq = probe.fq.get("quotient")
        if current_fq is None:
            all_signals.append(
                DriftSignal(
                    organ="arifflow",
                    metric="fq",
                    baseline_value=str(bl_fq),
                    current_value="null",
                    drift_delta="FQ_NULLIFIED",
                    severity="HIGH",
                    trend="DECAYING",
                )
            )
        elif not isinstance(current_fq, (int, float)):
            all_signals.append(
                DriftSignal(
                    organ="arifflow",
                    metric="fq",
                    baseline_value=str(bl_fq),
                    current_value=str(current_fq),
                    drift_delta="FQ_UNMEASURED",
                    severity="MEDIUM",
                    trend="STABLE",
                )
            )
        elif current_fq < (bl_fq or 1.0) * 0.5:
            all_signals.append(
                DriftSignal(
                    organ="arifflow",
                    metric="fq",
                    baseline_value=str(bl_fq),
                    current_value=str(current_fq),
                    drift_delta=f"{current_fq - (bl_fq or 0):+.3f}",
                    severity="CRITICAL",
                    trend="DECAYING",
                )
            )
        elif current_fq < (bl_fq or 1.0) * 0.8:
            all_signals.append(
                DriftSignal(
                    organ="arifflow",
                    metric="fq",
                    baseline_value=str(bl_fq),
                    current_value=str(current_fq),
                    drift_delta=f"{current_fq - (bl_fq or 0):+.3f}",
                    severity="MEDIUM",
                    trend="DECAYING",
                )
            )

    # Overall verdict
    criticals = sum(1 for s in all_signals if s.severity == "CRITICAL")
    highs = sum(1 for s in all_signals if s.severity == "HIGH")

    if criticals > 0:
        verdict = "CRITICAL"
    elif highs > 0:
        verdict = "DEGRADING"
    elif all_signals:
        verdict = "DRIFTING"
    else:
        verdict = "STABLE"

    return DriftReport(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        total_drifts=len(all_signals),
        signals=all_signals,
        overall_verdict=verdict,
    )
