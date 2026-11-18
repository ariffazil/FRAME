"""
FRAME — Federation Reference & Assessment Measurement Engine.
Configuration.
"""

import os

# ── Server ────────────────────────────────────────────────────────
FRAME_HOST = os.getenv("FRAME_HOST", "127.0.0.1")
FRAME_PORT = int(os.getenv("FRAME_PORT", "18085"))
FRAME_LOG_LEVEL = os.getenv("FRAME_LOG_LEVEL", "info")

# ── Organ & Agentic System Topology (ports to probe) ──────────────
ORGAN_PORTS = {
    # Core governance, domain & telemetry organs
    "arifos": 8088,
    "aforge": 7071,
    "aforge_mcp": 7072,
    "geox": 8081,
    "wealth": 18082,
    "well": 18083,
    "aaa": 3001,
    "signal": 18084,
    "arifflow": 7073,
    "fed": 7074,
    "hermes": 18087,
    "chron": 18102,
    # Shared model & agentic-tools gateway planes
    "litellm": 4000,
    "agentic_tools": 18430,
    # flame (:18901) RETIRED 2026-09-04 — legacy lane decommissioned, no systemd
    # unit exists and nothing listens. Removed 2026-10-20.
}

# ── Probe ─────────────────────────────────────────────────────────
PROBE_TIMEOUT_SECONDS = int(os.getenv("FRAME_PROBE_TIMEOUT", "5"))
PROBE_DEFAULT_INTERVAL_MINUTES = int(os.getenv("FRAME_PROBE_INTERVAL", "15"))

# ── Baseline ──────────────────────────────────────────────────────
BASELINE_FILE = os.getenv("FRAME_BASELINE_FILE", "/var/lib/frame/baseline.json")
BASELINE_DIR = os.path.dirname(BASELINE_FILE)

# ── Trend ─────────────────────────────────────────────────────────
TREND_FILE = os.getenv("FRAME_TREND_FILE", "/var/lib/frame/trends.jsonl")
MAX_TREND_ENTRIES = int(os.getenv("FRAME_MAX_TREND", "10000"))
MAX_TREND_GAP_SECONDS = float(os.getenv("FRAME_MAX_TREND_GAP", "3600"))  # 1h default

# ── Alert thresholds ──────────────────────────────────────────────
FQ_CRITICAL = float(os.getenv("FRAME_FQ_CRITICAL", "0.5"))
FQ_WARNING = float(os.getenv("FRAME_FQ_WARNING", "0.7"))
ORGAN_DOWN_THRESHOLD = int(os.getenv("FRAME_ORGAN_DOWN_THRESHOLD", "2"))  # consecutive probes
DRIFT_SEVERITY_THRESHOLD = float(os.getenv("FRAME_DRIFT_THRESHOLD", "0.3"))

# ── SIGNAL integration ────────────────────────────────────────────
SIGNAL_URL = os.getenv("FRAME_SIGNAL_URL", "http://127.0.0.1:18084")
