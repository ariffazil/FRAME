"""
FRAME — Federation Reference & Assessment Measurement Engine
Port: 18085 · Authority: ADVISORY_ONLY (measures, never mutates)

Six chambers:
  1. BASELINE — reference metrics for every organ/agent/floor
  2. PROBE    — live organ sampling
  3. COMPARE  — drift detection against baselines
  4. TREND    — time-series aggregation
  5. ALERT    — threshold escalation via SIGNAL
  6. REPORT   — daily institutional health brief
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from .baseline import (
    get_baseline,
    get_organ_baseline,
    get_federation_baseline,
    update_organ_baseline,
    load_baseline,
)
from .probe import probe_federation, probe_organ
from .compare import compare_federation
from .trend import append_trend, get_federation_trend, TrendPoint
from .rsi_verify import verify_monotonicity
from .alert import escalate_drift
from .report import generate_report
from .config import FRAME_PORT, FRAME_HOST, FRAME_LOG_LEVEL


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load baseline. Shutdown: no-op."""
    load_baseline()
    print(f"FRAME organ: baseline loaded, {len(get_baseline().get('organs', {}))} organs tracked")
    yield


app = FastAPI(
    title="FRAME Organ",
    description="Federation Reference & Assessment Measurement Engine",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Health ──────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    baseline = get_baseline()
    return {
        "status": "ok",
        "organ": "frame",
        "port": FRAME_PORT,
        "version": "1.0.0",
        "baseline_organs": len(baseline.get("organs", {})),
        "baseline_established": baseline.get("established_at", "unknown"),
        "chambers": {
            "baseline": "active",
            "probe": "active",
            "compare": "active",
            "trend": "active",
            "alert": "active",
            "report": "active",
            "rsi_verify": "active",
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ── Chamber 1: Baseline ────────────────────────────────────────────


@app.get("/frame/baseline")
async def frame_baseline():
    """Full baseline for all tracked organs and floors."""
    return get_baseline()


@app.get("/frame/baseline/{organ}")
async def frame_baseline_organ(organ: str):
    """Baseline for a specific organ."""
    bl = get_organ_baseline(organ)
    if not bl:
        return JSONResponse(status_code=404, content={"error": f"organ '{organ}' not in baseline"})
    return {organ: bl}


@app.post("/frame/baseline/{organ}")
async def frame_baseline_update(organ: str, metrics: dict):
    """Update baseline metrics for an organ."""
    update_organ_baseline(organ, metrics)
    return {"status": "updated", "organ": organ, "metrics": metrics}


# ── Chamber 2: Probe ───────────────────────────────────────────────


@app.get("/frame/probe")
async def frame_probe():
    """Probe all federation organs and return live health snapshot."""
    result = await probe_federation()

    # Append to trend log
    fq_val = result.fq.get("quotient") if result.fq and isinstance(result.fq, dict) else None
    append_trend(
        TrendPoint(
            timestamp=result.timestamp,
            epoch=time.time(),
            fq=fq_val,
            organs_up=result.healthy_organs,
            organs_total=result.total_organs,
            avg_latency_ms=sum(o.latency_ms for o in result.organs) / max(len(result.organs), 1),
            drift_count=0,
            verdict=result.fq.get("verdict", "UNKNOWN")
            if result.fq and isinstance(result.fq, dict)
            else "UNKNOWN",
        )
    )

    return result.model_dump()


@app.get("/frame/probe/{organ}")
async def frame_probe_organ(organ: str):
    """Probe a single organ."""
    from .config import ORGAN_PORTS

    port = ORGAN_PORTS.get(organ)
    if not port:
        return JSONResponse(status_code=404, content={"error": f"organ '{organ}' not in topology"})
    result = await probe_organ(organ, port)
    return result.model_dump()



# ── OBSERVER DOCTRINE HARDENING (2026-08-15, external audit) ────────
# Every observational payload carries authority + verdict_source so no
# consumer can mistake severity for a verdict (Gödel leak guard), and
# baselines older than 90d emit BASELINE_STALE as a meta-signal —
# refresh remains sovereign-gated, never automatic (anti-Goodhart).
import datetime as _dt

BASELINE_STALE_AFTER_DAYS = 90


def _observe(payload: dict) -> dict:
    payload["authority"] = "OBSERVATIONAL_ONLY"
    payload["verdict_source"] = None
    try:
        from .baseline import load_baseline
        est = (load_baseline() or {}).get("established_at", "")
        if est:
            age_days = (_dt.datetime.now(_dt.timezone.utc)
                        - _dt.datetime.strptime(est, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)).days
            payload["baseline_age_days"] = age_days
            payload["baseline_stale"] = age_days > BASELINE_STALE_AFTER_DAYS
    except Exception:
        pass
    return payload


# ── Chamber 3: Compare ─────────────────────────────────────────────


@app.get("/frame/drift")
async def frame_drift():
    """Run a full federation probe and compare against baselines."""
    probe = await probe_federation()
    drift = compare_federation(probe)
    return _observe(drift.model_dump())


# ── Chamber 4: Trend ───────────────────────────────────────────────


@app.get("/frame/trend")
async def frame_trend(hours: int = Query(default=24, ge=1, le=168)):
    """Get federation trend over specified time window."""
    trend = get_federation_trend(hours=hours)
    return trend.model_dump()


# ── Chamber 7: RSI VERIFY (verdict monotonicity) ──────────────────


@app.get("/frame/rsi-verify")
async def frame_rsi_verify():
    """Verify trend time-series monotonicity + cross-restart integrity.

    F11 AUDITABILITY guard — detects silent rollback, truncation, or replay
    on the FRAME trend log. Read-only. Pure verification, no mutation.
    """
    result = verify_monotonicity()
    return result.model_dump()


# ── Chamber 5: Alert ───────────────────────────────────────────────


@app.post("/frame/alert")
async def frame_alert():
    """Run drift detection and escalate via SIGNAL if thresholds exceeded."""
    probe = await probe_federation()
    drift = compare_federation(probe)
    alert_result = await escalate_drift(drift)
    return _observe({
        "drift": drift.model_dump(),
        "alert": alert_result,
    })


# ── Chamber 6: Report ──────────────────────────────────────────────


@app.get("/frame/report/{period}")
async def frame_report(period: str = "daily"):
    """Generate and return an institutional health report."""
    if period not in ("daily", "weekly"):
        period = "daily"

    probe = await probe_federation()
    drift = compare_federation(probe)
    trend = get_federation_trend(hours=24 if period == "daily" else 168)

    report = generate_report(probe=probe, drift=drift, trend=trend, period=period)
    return _observe(report.model_dump())


@app.get("/frame/report")
async def frame_report_default():
    """Default: daily report."""
    return await frame_report("daily")


# ── Entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "frame_organ.main:app",
        host=FRAME_HOST,
        port=FRAME_PORT,
        log_level=FRAME_LOG_LEVEL,
    )
