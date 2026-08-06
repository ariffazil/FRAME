"""
FRAME — Chamber 1: BASELINE
Maintains reference metrics for every organ, agent, and floor.
The reference frame against which all other measurements are compared.
"""

import json
import os
import time
from typing import Optional

from pydantic import BaseModel

from .config import BASELINE_FILE, BASELINE_DIR

# ── Default baseline template ─────────────────────────────────────

DEFAULT_BASELINE = {
    "version": 1,
    "established_at": "",
    "updated_at": "",
    "organs": {
        "arifos": {"health": "healthy", "latency_ms": 5, "floors": 13},
        "aforge": {"health": "healthy", "latency_ms": 8, "tools": 114},
        "geox": {"health": "healthy", "latency_ms": 12, "tools": 32},
        "wealth": {"health": "healthy", "latency_ms": 10, "tools": 12},
        "well": {"health": "healthy", "latency_ms": 8, "tools": 12},
        "aaa": {"health": "healthy", "latency_ms": 6, "tools": 1},
        "signal": {"health": "healthy", "latency_ms": 5, "chambers": 6},
        "arifflow": {"health": "healthy", "fq_optimal": 1.0, "fq_warning": 0.7, "fq_critical": 0.5},
        "fed": {"health": "healthy", "providers_alive": 8},
        "flame": {"health": "live", "mode": "RM0-TOOLS-FREELOOP"},
    },
    "floors": {
        "f1_amanah": {"violations": 0, "holds": 0},
        "f2_truth": {"epistemic_accuracy": 0.90},
        "f4_clarity": {"avg_delta_s": 0.0},
        "f7_humility": {"avg_omega": 0.04},
        "f8_genius": {"avg_g_score": 0.80},
        "f9_antihantu": {"fabrication_count": 0},
        "f13_sovereign": {"vetoes": 0},
    },
    "federation": {
        "total_organs": 10,
        "expected_organs_up": 10,
        "avg_fq": 1.0,
        "avg_latency_ms": 8,
    },
}

baseline: dict = {}


def _ensure_dir():
    os.makedirs(BASELINE_DIR, exist_ok=True)


def load_baseline() -> dict:
    """Load baseline from disk, or initialize defaults."""
    global baseline
    _ensure_dir()
    try:
        with open(BASELINE_FILE) as f:
            baseline = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        baseline = dict(DEFAULT_BASELINE)
        baseline["established_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        baseline["updated_at"] = baseline["established_at"]
        save_baseline()
    return baseline


def save_baseline():
    """Persist baseline to disk."""
    _ensure_dir()
    baseline["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=2)


def get_baseline() -> dict:
    """Return current baseline, loading if needed."""
    global baseline
    if not baseline:
        load_baseline()
    return baseline


def get_organ_baseline(organ: str) -> dict:
    """Return baseline for a specific organ."""
    return get_baseline().get("organs", {}).get(organ, {})


def update_organ_baseline(organ: str, metrics: dict):
    """Update baseline for an organ with new metrics."""
    b = get_baseline()
    if organ not in b.get("organs", {}):
        b.setdefault("organs", {})[organ] = {}
    b["organs"][organ].update(metrics)
    save_baseline()


def update_floor_baseline(floor: str, metrics: dict):
    """Update baseline for a constitutional floor."""
    b = get_baseline()
    if floor not in b.get("floors", {}):
        b.setdefault("floors", {})[floor] = {}
    b["floors"][floor].update(metrics)
    save_baseline()


def get_federation_baseline() -> dict:
    """Return federation-wide baseline."""
    return get_baseline().get("federation", {})
