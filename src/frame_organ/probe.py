"""
FRAME — Chamber 2: PROBE
Live sampling of all federation organs, agent gateways, and shared tools.
"""

import time
from typing import Optional

import httpx
from pydantic import BaseModel

from .config import ORGAN_PORTS, PROBE_TIMEOUT_SECONDS

# Organs/gateways whose /health is a deep dependency sweep rather than a fast
# liveness answer. FED (:7074) answers /health directly; LiteLLM (:4000) sweeps
# upstream providers on authenticated /health, whereas /health/liveliness
# answers immediately with a bare string ("I'm alive!").
HEALTH_PATH_OVERRIDES: dict[str, str] = {
    "litellm": "/health/liveliness",
}

DEEP_HEALTH_ORGANS: tuple[str, ...] = ("litellm",)


class OrganProbe(BaseModel):
    organ: str
    port: int
    healthy: bool
    latency_ms: float
    status: str = "unknown"
    details: dict = {}
    error: str = ""
    # Which path this probe measured so swapping deep vs liveness paths stays explicit.
    probe_path: str = "/health"


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
    """Probe a single organ or gateway health endpoint."""
    path = HEALTH_PATH_OVERRIDES.get(organ, "/health")
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            resp = await client.get(f"http://127.0.0.1:{port}{path}")
            latency = (time.monotonic() - start) * 1000
            data = (
                resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            if resp.status_code == 200 and isinstance(data, dict):
                status = data.get("status", "ok")
                if data.get("degraded_mode") is True and status in ("ok", "healthy"):
                    status = "degraded"
            else:
                status = "ok" if resp.status_code == 200 else "degraded"

            # F2 coherence rule: reachable != healthy. An organ answering 200
            # with status="degraded" or non-200 HTTP is DEGRADED, not healthy.
            is_healthy = resp.status_code == 200 and status not in (
                "degraded",
                "down",
                "unhealthy",
                "error",
            )
            return OrganProbe(
                organ=organ,
                port=port,
                healthy=is_healthy,
                latency_ms=round(latency, 2),
                status=status,
                details=data if isinstance(data, dict) else {"raw_status": resp.status_code},
                probe_path=path,
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
            probe_path=path,
        )


async def probe_federation() -> FederationProbe:
    """Probe all federation organs and return a complete health snapshot."""
    start = time.monotonic()

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
                    status="down",
                    error=str(result)[:120],
                    probe_path=HEALTH_PATH_OVERRIDES.get(organ, "/health"),
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

    # Partition counts cleanly so healthy + degraded + down == total.
    healthy = sum(1 for o in organ_list if o.healthy)
    degraded = sum(1 for o in organ_list if not o.healthy and o.status != "down")
    down = sum(1 for o in organ_list if not o.healthy and o.status == "down")
    total = len(organ_list)
    assert healthy + degraded + down == total, (
        f"Conservation invariant violated: {healthy}+{degraded}+{down} != {total}"
    )

    probe_duration = (time.monotonic() - start) * 1000

    return FederationProbe(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        total_organs=total,
        healthy_organs=healthy,
        degraded_organs=degraded,
        down_organs=down,
        organs=organ_list,
        fq=fq,
        probe_duration_ms=round(probe_duration, 2),
    )
