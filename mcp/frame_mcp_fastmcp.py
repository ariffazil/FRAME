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
from typing import Any

from fastmcp import FastMCP

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


@mcp.tool()
def frame_health() -> dict[str, Any]:
    """FRAME observer organ health — chamber status, baseline info,
    version. Read-only. OBSERVE_ONLY authority."""
    return _frame_get("/health")


@mcp.tool()
def frame_probe() -> dict[str, Any]:
    """Probe all federation organs and return live health snapshot.
    Shows which organs are up, latency, FQ state.
    Evidence only — never a verdict."""
    return _frame_get("/frame/probe")


@mcp.tool()
def frame_drift() -> dict[str, Any]:
    """Run full federation probe and compare against baselines.
    Returns drift signals — evidence of deviation from expected state.
    OBSERVATIONAL_ONLY: drift is evidence, not a verdict."""
    return _frame_get("/frame/drift")


@mcp.tool()
def frame_baseline() -> dict[str, Any]:
    """Get baseline metrics for all tracked organs and floors.
    Baselines are the expected-state reference for drift detection."""
    return _frame_get("/frame/baseline")


@mcp.tool()
def frame_trend(hours: int = 24) -> dict[str, Any]:
    """Federation trend over specified time window.
    Shows FQ, organ health, latency trends. Evidence only.

    Args:
        hours: Time window in hours (1-168, default 24)
    """
    return _frame_get(f"/frame/trend?hours={hours}")


@mcp.tool()
def frame_report(period: str = "daily") -> dict[str, Any]:
    """Generate institutional health report (daily or weekly).
    Combines probe + drift + trend into a single evidence report.
    OBSERVATIONAL_ONLY.

    Args:
        period: 'daily' or 'weekly'
    """
    return _frame_get(f"/frame/report/{period}")


@mcp.tool()
def frame_rsi_verify() -> dict[str, Any]:
    """Verify trend time-series monotonicity and cross-restart integrity.
    F11 AUDITABILITY guard — detects silent rollback, truncation, or replay.
    Read-only, pure verification."""
    return _frame_get("/frame/rsi-verify")


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=18086, json_response=True)
