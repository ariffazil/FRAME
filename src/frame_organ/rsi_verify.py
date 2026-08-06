"""
FRAME — Chamber 7: RSI VERIFY
Time-series monotonicity + cross-restart integrity guard.
F11 AUDITABILITY + F4 ΔS ≤ 0 — detects silent rollback or replay.

Why this chamber:
  trend.jsonl is append-only (good) but has no integrity check.
  If the file is edited, truncated, or replayed with stale timestamps,
  the trend appears healthy while reality is decayed.
  RSI VERIFY closes that gap — verify monotonicity on every read.

Two checks:
  1. Temporal monotonicity — every epoch > previous epoch
  2. Density check — gaps > MAX_GAP_SECONDS suggest truncation

Reversibility: pure read-only verification. No state mutation.
"""

import os
from typing import Optional

from pydantic import BaseModel

from .config import TREND_FILE, MAX_TREND_GAP_SECONDS
from .trend import read_trends


class MonotonicityViolation(BaseModel):
    index: int
    timestamp: str
    epoch: float
    previous_timestamp: Optional[str] = None
    previous_epoch: Optional[float] = None
    delta_seconds: float = 0.0
    kind: str  # "non_monotonic" | "gap_exceeded" | "duplicate_epoch"


class RsiVerifyResult(BaseModel):
    monotonic: bool
    checked_points: int
    violations: list[MonotonicityViolation]
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None
    span_seconds: float = 0.0
    verdict: str  # "PASS" | "CAUTION" | "VOID"


def verify_monotonicity(
    trend_file: str = TREND_FILE,
    max_gap_seconds: float = MAX_TREND_GAP_SECONDS,
) -> RsiVerifyResult:
    """Verify the trend time-series is monotonically increasing.

    Reads TREND_FILE, checks every point's epoch > previous point's epoch.
    Gaps > max_gap_seconds are flagged as CAUTION (not VOID — gaps are
    legitimate when the trend collector is paused).
    """
    points = read_trends(limit=10000)

    violations: list[MonotonicityViolation] = []
    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]
        delta = curr.epoch - prev.epoch

        if delta <= 0:
            # Non-monotonic or duplicate — VOID candidate
            kind = "duplicate_epoch" if delta == 0 else "non_monotonic"
            violations.append(
                MonotonicityViolation(
                    index=i,
                    timestamp=curr.timestamp,
                    epoch=curr.epoch,
                    previous_timestamp=prev.timestamp,
                    previous_epoch=prev.epoch,
                    delta_seconds=delta,
                    kind=kind,
                )
            )
        elif delta > max_gap_seconds:
            # Gap exceeds threshold — CAUTION, not VOID
            violations.append(
                MonotonicityViolation(
                    index=i,
                    timestamp=curr.timestamp,
                    epoch=curr.epoch,
                    previous_timestamp=prev.timestamp,
                    previous_epoch=prev.epoch,
                    delta_seconds=delta,
                    kind="gap_exceeded",
                )
            )

    # Determine verdict
    fatal_violations = [v for v in violations if v.kind in ("non_monotonic", "duplicate_epoch")]
    if fatal_violations:
        verdict = "VOID"
        monotonic = False
    elif violations:
        verdict = "CAUTION"
        monotonic = True  # gaps are still monotonic, just sparse
    else:
        verdict = "PASS"
        monotonic = True

    first_ts = points[0].timestamp if points else None
    last_ts = points[-1].timestamp if points else None
    span = (points[-1].epoch - points[0].epoch) if len(points) >= 2 else 0.0

    return RsiVerifyResult(
        monotonic=monotonic,
        checked_points=len(points),
        violations=violations,
        first_timestamp=first_ts,
        last_timestamp=last_ts,
        span_seconds=span,
        verdict=verdict,
    )
