"""
FRAME — Chamber 4: TREND
Time-series aggregation. Detects improvement/decay/oscillation patterns.
"""

import json
import os
import time
from collections import defaultdict
from typing import Optional

from pydantic import BaseModel

from .config import TREND_FILE, MAX_TREND_ENTRIES


class TrendPoint(BaseModel):
    timestamp: str
    epoch: float
    fq: Optional[float] = None
    organs_up: int = 0
    organs_total: int = 0
    avg_latency_ms: float = 0
    drift_count: int = 0
    verdict: str = "UNKNOWN"


class TrendSeries(BaseModel):
    organ: str
    points: list[TrendPoint]
    direction: str  # "IMPROVING" | "STABLE" | "DECAYING" | "OSCILLATING"
    slope: float  # rate of change per hour


def _ensure_dir():
    os.makedirs(os.path.dirname(TREND_FILE), exist_ok=True)


def append_trend(point: TrendPoint):
    """Append a trend point to the time-series log."""
    _ensure_dir()
    with open(TREND_FILE, "a") as f:
        f.write(point.model_dump_json() + "\n")

    # Prune old entries if over max
    _prune_trends()


def _prune_trends():
    """Keep only the most recent MAX_TREND_ENTRIES."""
    try:
        with open(TREND_FILE) as f:
            lines = f.readlines()
        if len(lines) > MAX_TREND_ENTRIES:
            with open(TREND_FILE, "w") as f:
                f.writelines(lines[-MAX_TREND_ENTRIES:])
    except FileNotFoundError:
        pass


def read_trends(limit: int = 100) -> list[TrendPoint]:
    """Read recent trend points."""
    try:
        with open(TREND_FILE) as f:
            lines = f.readlines()[-limit:]
        points = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    points.append(TrendPoint(**json.loads(line)))
                except Exception:
                    pass
        return points
    except FileNotFoundError:
        return []


def compute_trend(points: list[TrendPoint]) -> tuple[str, float]:
    """
    Compute trend direction and slope from a list of points.
    Uses simple linear regression on epoch vs FQ.
    Returns (direction, slope_per_hour).
    """
    if len(points) < 2:
        return ("STABLE", 0.0)

    n = len(points)
    epochs = [p.epoch for p in points]
    fqs = [p.fq or 1.0 for p in points]

    mean_x = sum(epochs) / n
    mean_y = sum(fqs) / n

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(epochs, fqs))
    den = sum((x - mean_x) ** 2 for x in epochs)

    if den == 0:
        return ("STABLE", 0.0)

    slope = num / den
    # Convert to slope per hour (epoch is in seconds)
    slope_per_hour = slope * 3600

    # Direction classification
    if abs(slope_per_hour) < 0.001:
        direction = "STABLE"
    elif slope_per_hour > 0:
        direction = "IMPROVING"
    else:
        direction = "DECAYING"

    # Detect oscillation: alternating signs
    if n >= 4:
        sign_changes = sum(
            1 for i in range(1, n) if (fqs[i] - fqs[i - 1]) * (fqs[i - 1] - fqs[i - 2]) < 0
        )
        if sign_changes >= n // 2:
            direction = "OSCILLATING"

    return (direction, round(slope_per_hour, 6))


def get_federation_trend(hours: int = 24) -> TrendSeries:
    """Get federation-wide trend over the specified time window."""
    all_points = read_trends(limit=500)
    cutoff = time.time() - (hours * 3600)
    recent = [p for p in all_points if p.epoch > cutoff]

    direction, slope = compute_trend(recent)

    return TrendSeries(
        organ="federation",
        points=recent[-50:],  # Return last 50 points max
        direction=direction,
        slope=slope,
    )
