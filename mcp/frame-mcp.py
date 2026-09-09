#!/usr/bin/env python3
"""
FRAME MCP shim — bridges MCP stdio (JSON-RPC) to the FRAME observer organ
on 127.0.0.1:18085.

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

Stdlib only. MCP stdio = newline-delimited JSON-RPC 2.0.
"""

import json
import sys
import urllib.request
import urllib.error

FRAME_HOST = "127.0.0.1"
FRAME_PORT = 18085
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "frame_health",
        "description": (
            "FRAME observer organ health — chamber status, baseline info, "
            "version. Read-only. OBSERVE_ONLY authority."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "frame_probe",
        "description": (
            "Probe all federation organs and return live health snapshot. "
            "Shows which organs are up, latency, FQ state. "
            "Evidence only — never a verdict."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "frame_drift",
        "description": (
            "Run full federation probe and compare against baselines. "
            "Returns drift signals — evidence of deviation from expected state. "
            "OBSERVATIONAL_ONLY: drift is evidence, not a verdict."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "frame_baseline",
        "description": (
            "Get baseline metrics for all tracked organs and floors. "
            "Baselines are the expected-state reference for drift detection."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "frame_trend",
        "description": (
            "Federation trend over specified time window. "
            "Shows FQ, organ health, latency trends. Evidence only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Time window in hours (1-168, default 24)",
                    "default": 24,
                    "minimum": 1,
                    "maximum": 168,
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "frame_report",
        "description": (
            "Generate institutional health report (daily or weekly). "
            "Combines probe + drift + trend into a single evidence report. "
            "OBSERVATIONAL_ONLY."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["daily", "weekly"],
                    "default": "daily",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "frame_rsi_verify",
        "description": (
            "Verify trend time-series monotonicity and cross-restart integrity. "
            "F11 AUDITABILITY guard — detects silent rollback, truncation, or replay. "
            "Read-only, pure verification."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]


def frame_get(path: str) -> dict:
    """HTTP GET to FRAME daemon via urllib (handles chunked encoding)."""
    url = f"http://{FRAME_HOST}:{FRAME_PORT}{path}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": str(e), "status_code": e.code}


def call_tool(name: str, args: dict) -> dict:
    if name == "frame_health":
        return frame_get("/health")
    if name == "frame_probe":
        return frame_get("/frame/probe")
    if name == "frame_drift":
        return frame_get("/frame/drift")
    if name == "frame_baseline":
        return frame_get("/frame/baseline")
    if name == "frame_trend":
        hours = args.get("hours", 24)
        return frame_get(f"/frame/trend?hours={hours}")
    if name == "frame_report":
        period = args.get("period", "daily")
        return frame_get(f"/frame/report/{period}")
    if name == "frame_rsi_verify":
        return frame_get("/frame/rsi-verify")
    raise ValueError(f"unknown tool: {name}")


def respond(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        out["error"] = error
    else:
        out["result"] = result
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method", "")
        msg_id = msg.get("id")

        if method == "initialize":
            respond(
                msg_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "frame", "version": "1.0.0"},
                },
            )
        elif method == "ping":
            respond(msg_id, {})
        elif method and method.startswith("notifications/"):
            continue
        elif method == "tools/list":
            respond(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params", {})
            tname = params.get("name", "")
            targs = params.get("arguments", {}) or {}
            try:
                result = call_tool(tname, targs)
                respond(
                    msg_id,
                    {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ],
                        "isError": False,
                    },
                )
            except Exception as e:
                respond(
                    msg_id,
                    {
                        "content": [{"type": "text", "text": f"FRAME error: {e}"}],
                        "isError": True,
                    },
                )
        else:
            if msg_id is not None:
                respond(
                    msg_id,
                    error={"code": -32601, "message": f"method not found: {method}"},
                )


if __name__ == "__main__":
    main()
