"""
FRAME — Chamber 5: ALERT
Threshold-based escalation. Routes drift events to SIGNAL kabarkan.
"""

import httpx

from .compare import DriftReport, DriftSignal
from .config import SIGNAL_URL, PROBE_TIMEOUT_SECONDS


async def escalate_drift(report: DriftReport) -> dict:
    """Escalate a drift report to SIGNAL for kabarkan dispatch."""
    if report.overall_verdict == "STABLE":
        return {"sent": False, "reason": "stable_no_alert"}

    # SUPPRESS chamber (2026-08-15, observer-fatigue hardening):
    # identical drift signature collapses to one alert per 24h window.
    import json as _json
    import os as _os
    import time as _time
    state_path = "/var/lib/frame/alert_state.json"  # ReadWritePaths-sanctioned (ProtectHome blocks /root)
    key = "|".join(sorted(f"{s.organ}/{s.metric}" for s in report.signals))
    now = _time.time()
    try:
        state = _json.load(open(state_path)) if _os.path.exists(state_path) else {}
    except Exception:
        state = {}
    if state.get("key") == key and now - state.get("ts", 0) < 86400:
        return {"sent": False, "reason": "suppressed_duplicate_24h", "severity": "CRITICAL" if report.overall_verdict == "CRITICAL" else "HIGH"}
    try:
        _os.makedirs(_os.path.dirname(state_path), exist_ok=True)
        _json.dump({"key": key, "ts": now}, open(state_path, "w"))
    except Exception:
        pass

    severity = "MEDIUM"
    is_breach = False
    requires_sovereign = False

    if report.overall_verdict == "CRITICAL":
        severity = "CRITICAL"
        requires_sovereign = True
    elif report.overall_verdict == "DEGRADING":
        severity = "HIGH"

    # Build alert body
    signal_lines = [
        f"- {s.organ}/{s.metric}: {s.current_value} (was {s.baseline_value}) [{s.severity}]"
        for s in report.signals[:5]
    ]
    body = f"Drift detected: {report.total_drifts} signals\n" + "\n".join(signal_lines)

    title = f"FRAME: Federation {report.overall_verdict} — {report.total_drifts} drift signals"

    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{SIGNAL_URL}/kabarkan/broadcast",
                json={
                    "title": title,
                    "body": body,
                    "source_organ": "frame",
                    "event_type": f"DRIFT_{report.overall_verdict}",
                    "severity": severity,
                    "is_constitutional_breach": is_breach,
                    "requires_sovereign": requires_sovereign,
                },
            )
            return (
                resp.json()
                if resp.status_code in (200, 202)
                else {"sent": False, "error": f"HTTP {resp.status_code}"}
            )
    except Exception as exc:
        return {"sent": False, "error": str(exc)[:120]}


async def alert_on_organ_down(organ: str, consecutive: int) -> dict:
    """Alert when an organ has been down for consecutive probes."""
    if consecutive < 2:
        return {"sent": False, "reason": "below_threshold"}

    severity = "CRITICAL" if consecutive >= 5 else "HIGH"

    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{SIGNAL_URL}/kabarkan/broadcast",
                json={
                    "title": f"FRAME: {organ} DOWN — {consecutive} consecutive probes",
                    "body": f"Organ {organ} has been unreachable for {consecutive} consecutive probes.",
                    "source_organ": "frame",
                    "event_type": "ORGAN_DOWN",
                    "severity": severity,
                    "requires_sovereign": severity == "CRITICAL",
                },
            )
            return resp.json() if resp.status_code in (200, 202) else {"sent": False}
    except Exception:
        return {"sent": False, "error": "signal_unreachable"}
