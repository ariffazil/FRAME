"""
FRAME — Chamber 7: REJECTION
Unified rejection telemetry across all federation organs.
Reads from /var/lib/frame/rejections.jsonl (populated by rejection_collector.py).
"""

import json
import os
import time
from collections import Counter
from typing import Optional

from pydantic import BaseModel

REJECTION_FILE = os.getenv(
    "FRAME_REJECTION_FILE", "/var/lib/frame/rejections.jsonl"
)
MAX_REJECTION_ENTRIES = int(os.getenv("FRAME_MAX_REJECTIONS", "50000"))


class RejectionEvent(BaseModel):
    timestamp: str
    source: str
    organ: str
    event_type: str
    severity: str
    detail: str
    raw_ref: str = ""


class RejectionSummary(BaseModel):
    timestamp: str
    total_events: int
    by_organ: dict
    by_type: dict
    by_severity: dict
    by_source: dict
    recent_events: list
    rejection_rate: dict


def load_rejections(
    limit: int = 100,
    organ: Optional[str] = None,
    source: Optional[str] = None,
    severity: Optional[str] = None,
    since: Optional[str] = None,
) -> list[dict]:
    """Load rejection events with optional filters."""
    events = []
    if not os.path.exists(REJECTION_FILE):
        return events

    with open(REJECTION_FILE) as f:
        for line in f:
            try:
                ev = json.loads(line.strip())
                if organ and ev.get("organ") != organ:
                    continue
                if source and ev.get("source") != source:
                    continue
                if severity and ev.get("severity") != severity:
                    continue
                if since:
                    ts = str(ev.get("timestamp", ""))
                    if ts < since:
                        continue
                events.append(ev)
            except json.JSONDecodeError:
                pass

    return events[-limit:]


def get_rejection_summary(hours: int = 24) -> RejectionSummary:
    """Generate rejection summary for the last N hours."""
    import datetime

    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(hours=hours)
    ).isoformat()

    events = load_rejections(limit=MAX_REJECTION_ENTRIES, since=cutoff)

    by_organ = Counter()
    by_type = Counter()
    by_severity = Counter()
    by_source = Counter()

    for ev in events:
        by_organ[ev.get("organ", "unknown")] += 1
        by_type[ev.get("event_type", "unknown")] += 1
        by_severity[ev.get("severity", "unknown")] += 1
        by_source[ev.get("source", "unknown")] += 1

    # Compute rejection rate per organ (rejections / total calls)
    # Total calls from probe data would be ideal; approximate from event counts
    rejection_rate = {}
    for organ, count in by_organ.items():
        rejection_rate[organ] = {
            "rejection_count": count,
            "period_hours": hours,
        }

    return RejectionSummary(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        total_events=len(events),
        by_organ=dict(by_organ),
        by_type=dict(by_type),
        by_severity=dict(by_severity),
        by_source=dict(by_source),
        recent_events=events[-20:],  # Last 20 for detail view
        rejection_rate=rejection_rate,
    )
