"""
FRAME — Chamber 2: PROBE
Live organ sampling. Hits every organ's /health endpoint and returns structured metrics.
"""

import time
from typing import Optional

import httpx
from pydantic import BaseModel

from .config import ORGAN_PORTS, PROBE_TIMEOUT_SECONDS


class OrganProbe(BaseModel):
    organ: str
    port: int
    healthy: bool
    latency_ms: float
    status: str = "unknown"
    details: dict = {}
    error: str = ""


class FederationProbe(BaseModel):
    timestamp: str
    total_organs: int
    healthy_organs: int
    degraded_organs: int
    down_organs: int
    organs: list[OrganProbe]
    fq: Optional[dict] = None
    probe_duration_ms: float = 0


async def probe_organ(organ: str, port: int) -> OrganProbe:
    """Probe a single organ's /health endpoint."""
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            resp = await client.get(f"http://127.0.0.1:{port}/health")
            latency = (time.monotonic() - start) * 1000
            data = (
                resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            status = data.get("status", "ok") if resp.status_code == 200 else "degraded"
            return OrganProbe(
                organ=organ,
                port=port,
                healthy=resp.status_code == 200,
                latency_ms=round(latency, 2),
                status=status,
                details=data if isinstance(data, dict) else {"raw_status": resp.status_code},
            )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return OrganProbe(
            organ=organ,
            port=port,
            healthy=False,
            latency_ms=round(latency, 2),
            status="down",
            details={},
            error=str(exc)[:120],
        )


async def probe_federation() -> FederationProbe:
    """Probe all federation organs and return a complete health snapshot."""
    start = time.monotonic()
    organs = []

    # Probe all organs concurrently
    import asyncio

    tasks = {organ: probe_organ(organ, port) for organ, port in ORGAN_PORTS.items()}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    organ_list = []
    for (organ, _), result in zip(tasks.items(), results):
        if isinstance(result, Exception):
            organ_list.append(
                OrganProbe(
                    organ=organ,
                    port=ORGAN_PORTS[organ],
                    healthy=False,
                    latency_ms=0,
                    status="error",
                    error=str(result)[:120],
                )
            )
        else:
            organ_list.append(result)

    # Extract FQ from arifflow probe if available
    fq = None
    for o in organ_list:
        if o.organ == "arifflow" and o.healthy:
            fq_data = o.details.get("fq", {})
            if isinstance(fq_data, dict):
                fq = fq_data

    healthy = sum(1 for o in organ_list if o.healthy)
    total = len(organ_list)

    probe_duration = (time.monotonic() - start) * 1000

    return FederationProbe(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        total_organs=total,
        healthy_organs=healthy,
        degraded_organs=sum(1 for o in organ_list if not o.healthy and o.status != "down"),
        down_organs=total - healthy,
        organs=organ_list,
        fq=fq,
        probe_duration_ms=round(probe_duration, 2),
    )
