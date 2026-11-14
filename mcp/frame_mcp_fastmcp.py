"""
FRAME MCP Server — FastMCP (replaces stdio shim frame-mcp.py)

FRAME is OBSERVE_ONLY — its output is evidence, never a verdict.
Every payload carries authority="OBSERVATIONAL_ONLY".

Tools:
  frame_health      — GET /health: chamber status, baseline info
  frame_probe       — GET /frame/probe: probe all federation organs
  frame_drift       — GET /frame/drift: compare live state vs baselines
  frame_baseline    — GET /frame/baseline: get all baselines
  frame_trend       — GET /frame/trend: federation trend over time window
  frame_report      — GET /frame/report/{period}: institutional health report
  frame_rsi_verify  — GET /frame/rsi-verify: verdict monotonicity check

DITEMPA BUKAN DIBERI — Forged, Not Given.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Literal

from fastmcp import FastMCP
from pydantic import Field

FRAME_HOST = "127.0.0.1"
FRAME_PORT = 18085

mcp = FastMCP(
    name="frame-mcp",
    version="2026.09.14",
    instructions=(
        "FRAME — Observer organ for arifOS Federation. "
        "Authority: OBSERVE_ONLY. Drift detection, evidence gathering. "
        "Its output is evidence, never a verdict."
    ),
)


def _frame_get(path: str) -> dict[str, Any]:
    """HTTP GET to FRAME daemon."""
    url = f"http://{FRAME_HOST}:{FRAME_PORT}{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": str(e), "status_code": e.code}
    except urllib.error.URLError as e:
        return {"error": f"FRAME daemon unreachable: {e.reason}"}


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
def frame_health() -> dict[str, Any]:
    """FRAME organ self-health — chamber status, baseline info, version.
    Use for FRAME itself; for federation organ liveness use frame_probe.
    Read-only. OBSERVE_ONLY authority — evidence, never a verdict."""
    return _frame_get("/health")


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def frame_probe() -> dict[str, Any]:
    """Probe all federation organs — live point-in-time snapshot (up/down,
    latency, FQ state). For divergence from expected state use frame_drift;
    for history use frame_trend. Evidence only — never a verdict."""
    return _frame_get("/frame/probe")


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def frame_drift() -> dict[str, Any]:
    """Run full federation probe and compare against baselines — answers
    'what drifted from expected state?'. For the raw snapshot use frame_probe;
    for the baseline values themselves use frame_baseline; for AGENT-session
    metrics (not organs) use frame_behavioral_drift.
    OBSERVATIONAL_ONLY: drift is evidence, not a verdict."""
    return _frame_get("/frame/drift")


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
def frame_baseline() -> dict[str, Any]:
    """Get the baseline metrics themselves — the expected-state reference for
    drift detection (all tracked organs and floors). For live comparison
    against these baselines use frame_drift. Read-only."""
    return _frame_get("/frame/baseline")


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def frame_trend(
    hours: int = Field(
        default=24, ge=1, le=168, description="Time window in hours (1-168, default 24)"
    ),
) -> dict[str, Any]:
    """Federation trend over a time window — FQ, organ health and latency as
    a time series. Use for 'how did it change?'; for the current instant use
    frame_probe. Evidence only — never a verdict.

    Args:
        hours: Time window in hours (1-168, default 24)
    """
    return _frame_get(f"/frame/trend?hours={hours}")


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})
def frame_report(period: Literal["daily", "weekly"] = "daily") -> dict[str, Any]:
    """Generate the institutional health report — combines probe + drift +
    trend into one periodic evidence packet. For a single component call
    frame_probe / frame_drift / frame_trend directly. OBSERVATIONAL_ONLY —
    evidence, never a verdict.

    Args:
        period: 'daily' or 'weekly' (enum-enforced on the wire; invalid values are rejected)
    """
    return _frame_get(f"/frame/report/{period}")


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
def frame_rsi_verify() -> dict[str, Any]:
    """Verify FRAME's own trend time-series — monotonicity and cross-restart
    integrity (F11 AUDITABILITY guard: detects silent rollback, truncation,
    replay of FRAME records). Not a probe of other organs — use frame_probe
    for that. Read-only, pure verification; evidence, never a verdict."""
    return _frame_get("/frame/rsi-verify")


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
def frame_behavioral_drift(
    tool_calls: list[str] | None = None,
    agent_responses: list[str] | None = None,
    response_lengths: list[int] | None = None,
    receipt_bytes: int = 0,
    output_bytes: int = 0,
    shadow_triggers: int = 0,
    total_interactions: int = 0,
) -> dict[str, Any]:
    """Compute behavioral drift metrics for an AGENT SESSION (not organs —
    for organ deviation use frame_drift). Returns 5 metrics:
    tool_call_entropy, question_back_rate, verbosity_drift,
    receipt_output_ratio, shadow_activation_rate. Pure computation, no I/O.
    OBSERVATIONAL_ONLY — evidence, never a verdict.

    Args:
        tool_calls: List of tool names called in session
        agent_responses: List of agent response texts
        response_lengths: List of response lengths over time
        receipt_bytes: Total receipt metadata bytes
        output_bytes: Total useful output bytes
        shadow_triggers: Number of shadow checks triggered
        total_interactions: Total interactions in session
    """
    import sys

    sys.path.insert(0, "/root/arifOS/arifosmcp/tools")
    from frame_behavioral_drift import compute_all, report

    metrics = compute_all(
        tool_calls=tool_calls,
        agent_responses=agent_responses,
        response_lengths=response_lengths,
        receipt_bytes=receipt_bytes,
        output_bytes=output_bytes,
        shadow_triggers=shadow_triggers,
        total_interactions=total_interactions,
    )
    return {
        "authority": "OBSERVATIONAL_ONLY",
        "metrics": [
            {
                "metric_id": m.metric_id,
                "name": m.name,
                "value": m.value,
                "baseline": m.baseline,
                "threshold": m.threshold,
                "status": m.status,
                "interpretation": m.interpretation,
            }
            for m in metrics
        ],
        "alerts": [m.name for m in metrics if m.status == "ALERT"],
        "warnings": [m.name for m in metrics if m.status == "WARNING"],
        "report": report(metrics),
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=18086, json_response=True)
