"""
FRAME — Chamber 2: PROBE
Live organ sampling. Hits every organ's /health endpoint and returns structured metrics.
"""

import time
from typing import Optional

import httpx
from pydantic import BaseModel

from .config import ORGAN_PORTS, PROBE_TIMEOUT_SECONDS

# 2026-10-28: organs whose /health is a DEEP dependency sweep rather than a
# liveness answer. FED :4000 proxies to litellm :4013 where an authenticated
# /health sweeps upstream providers (measured >10 s on a swapping host) while
# /health/liveliness answers in 1.8 ms. Probing the deep path from a monitor
# records "provider slow" as "FED slow" — a different claim.
HEALTH_PATH_OVERRIDES: dict[str, str] = {
    "fed": "/health/liveliness",
}

# Kept explicit so the omission is a decision, not a side effect: this monitor
# no longer exercises FED's provider sweep. If that sweep needs an alarm, it
# needs its own probe with its own threshold — not a slower organ latency.
DEEP_HEALTH_ORGANS: tuple[str, ...] = ("fed",)


class OrganProbe(BaseModel):
    organ: str
    port: int
    healthy: bool
    latency_ms: float
    status: str = "unknown"
    details: dict = {}
    error: str = ""
    # 2026-10-28: which path this latency measured. Without it, swapping a deep
    # health check for a liveness check silently changes what latency_ms means.
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
    """Probe a single organ's health endpoint.

    2026-10-28 — WHY SOME ORGANS USE A CHEAPER PATH.

    FED :4000 proxies to litellm :4013. Unauthenticated :4013/health answers in
    17 ms (401) while an AUTHENTICATED /health performs a full upstream-provider
    sweep and was measured hanging past 10 s on this host. FRAME probes from
    127.0.0.1, which HAProxy injects with the master key — so FRAME was probing
    the expensive branch and recording it as fed latency. /health/liveliness
    answers in 1.8 ms and /health/readiness in 9.7 ms.

    The probe path is recorded on every OrganProbe so the metric names what it
    measured. The deep provider sweep still needs an owner — dropping it here
    would trade a slow signal for a blind one; see DEEP_HEALTH_ORGANS.
    """
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
            # litellm's /health/liveliness answers with a bare JSON string
            # ("I'm alive!"), not an object — .get() on it raises and would be
            # recorded as "down". Accept any 200 as alive; only read `status`
            # when the body really is a mapping.
            if resp.status_code == 200 and isinstance(data, dict):
                status = data.get("status", "ok")
            else:
                status = "ok" if resp.status_code == 200 else "degraded"
            return OrganProbe(
                organ=organ,
                port=port,
                healthy=resp.status_code == 200,
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

    # 2026-10-21: healthy = SIHAT, bukan sekadar "boleh dihubungi". Sebelum ini
    # organ HTTP-200-dengan-status-degraded dikira healthy (healthy=9,
    # degraded=0 padahal 4 rekod status=degraded) — "reachable" dipaparkan
    # sebagai "sihat" (laporan luar 2026-10-21). Kelas kini koheren dan
    # lengkap (status armada pelbagai: ok/healthy/ok-v3-vector):
    #   healthy  = reachable DAN status != degraded (badan sihat secara deklarasi sendiri)
    #   degraded = status == degraded (reachable tapi tak sihat, termasuk non-200)
    #   down     = tak boleh dihubungi (exception/down/error)
    healthy = sum(1 for o in organ_list if o.healthy and o.status != "degraded")
    degraded = sum(1 for o in organ_list if o.status == "degraded")
    down = sum(1 for o in organ_list if not o.healthy)
    total = len(organ_list)

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
