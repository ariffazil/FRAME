"""Hermetic unit and contract tests for frame_organ and frame_mcp_fastmcp."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from frame_organ import alert, baseline, compare, config, main, probe


def test_topology_aligned_and_retired_flame_absent():
    assert "flame" not in config.ORGAN_PORTS
    for expected in (
        "arifos",
        "aforge",
        "aforge_mcp",
        "geox",
        "wealth",
        "well",
        "aaa",
        "signal",
        "arifflow",
        "fed",
        "hermes",
        "chron",
        "litellm",
        "agentic_tools",
    ):
        assert expected in config.ORGAN_PORTS
    assert config.PROBE_TIMEOUT_SECONDS >= 4


def test_fed_uses_health_and_litellm_uses_liveliness():
    assert "fed" not in probe.HEALTH_PATH_OVERRIDES
    assert probe.HEALTH_PATH_OVERRIDES["litellm"] == "/health/liveliness"
    assert probe.DEEP_HEALTH_ORGANS == ("litellm",)


@pytest.mark.asyncio
async def test_probe_organ_handles_degraded_and_string_json(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.port == 4000 and request.url.path == "/health/liveliness":
            return httpx.Response(200, json="I'm alive!")
        if request.url.port == 8088:
            return httpx.Response(200, json={"status": "degraded"})
        if request.url.port == 7071:
            return httpx.Response(200, json={"ok": False, "degraded_mode": True, "status": "ok"})
        if request.url.port == 7074:
            return httpx.Response(200, json={"status": "healthy"})
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    class MockClient(real_async_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(probe.httpx, "AsyncClient", MockClient)

    litellm = await probe.probe_organ("litellm", 4000)
    assert litellm.healthy is True
    assert litellm.status == "ok"
    assert litellm.probe_path == "/health/liveliness"

    fed = await probe.probe_organ("fed", 7074)
    assert fed.healthy is True
    assert fed.status == "healthy"
    assert fed.probe_path == "/health"

    arifos = await probe.probe_organ("arifos", 8088)
    assert arifos.healthy is False
    assert arifos.status == "degraded"

    aforge = await probe.probe_organ("aforge", 7071)
    assert aforge.healthy is False
    assert aforge.status == "degraded"

    down = await probe.probe_organ("chron", 18102)
    assert down.healthy is False
    assert down.status == "down"


@pytest.mark.asyncio
async def test_probe_federation_conservation_invariant(monkeypatch):
    async def fake_probe(organ: str, port: int) -> probe.OrganProbe:
        if organ in ("arifos", "well"):
            return probe.OrganProbe(organ=organ, port=port, healthy=False, latency_ms=10.0, status="degraded")
        if organ == "chron":
            return probe.OrganProbe(organ=organ, port=port, healthy=False, latency_ms=10.0, status="down")
        if organ == "arifflow":
            return probe.OrganProbe(
                organ=organ,
                port=port,
                healthy=True,
                latency_ms=5.0,
                status="ok-v3-vector",
                details={"fq": {"quotient": 1.0, "verdict": "OPTIMAL"}},
            )
        return probe.OrganProbe(organ=organ, port=port, healthy=True, latency_ms=5.0, status="healthy")

    monkeypatch.setattr(probe, "probe_organ", fake_probe)
    snap = await probe.probe_federation()
    assert snap.total_organs == len(config.ORGAN_PORTS)
    assert snap.healthy_organs + snap.degraded_organs + snap.down_organs == snap.total_organs
    assert snap.degraded_organs == 2
    assert snap.down_organs == 1
    assert snap.fq == {"quotient": 1.0, "verdict": "OPTIMAL"}


def test_compare_applies_250ms_latency_floor(tmp_path, monkeypatch):
    monkeypatch.setattr(baseline, "BASELINE_FILE", str(tmp_path / "baseline.json"))
    monkeypatch.setattr(baseline, "BASELINE_DIR", str(tmp_path))
    baseline.baseline.clear()
    baseline.load_baseline()
    baseline.update_organ_baseline("fed", {"health": "healthy", "latency_ms": 10.0})

    fast_spike = probe.OrganProbe(organ="fed", port=7074, healthy=True, latency_ms=120.0, status="healthy")
    assert compare.compare_organ(fast_spike) == []

    real_slow = probe.OrganProbe(organ="fed", port=7074, healthy=True, latency_ms=300.0, status="healthy")
    signals = compare.compare_organ(real_slow)
    assert len(signals) == 1
    assert signals[0].metric == "latency_ms"


def test_fastapi_health_and_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(baseline, "BASELINE_FILE", str(tmp_path / "baseline.json"))
    monkeypatch.setattr(baseline, "BASELINE_DIR", str(tmp_path))
    baseline.baseline.clear()
    with TestClient(main.app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["organ"] == "frame"
        assert body["baseline_organs"] == len(config.ORGAN_PORTS)
        assert len(body["chambers"]) == 9


def test_frame_mcp_registers_10_read_only_tools():
    pytest.importorskip("fastmcp")
    mcp_path = Path(__file__).resolve().parent.parent / "mcp" / "frame_mcp_fastmcp.py"
    spec = importlib.util.spec_from_file_location("frame_mcp_fastmcp", mcp_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    import asyncio

    tools = asyncio.run(mod.mcp.list_tools())
    names = {t.name for t in tools}
    assert len(names) == 11
    assert {"frame_witness", "frame_witness_action", "frame_rejections", "frame_probe", "frame_drift"}.issubset(names)
    for t in tools:
        assert t.annotations is not None
        assert getattr(t.annotations, "read_only_hint", None) is True or getattr(t.annotations, "readOnlyHint", None) is True


def test_per_action_witness_allowed_denied_and_unverified(tmp_path, monkeypatch):
    from frame_organ import witness

    monkeypatch.setattr(witness, "WITNESS_ROOTS", (str(tmp_path),))
    target = tmp_path / "staging.json"
    target.write_text('{"seq": 0}\n', encoding="utf-8")
    snap_before = witness.capture_target_snapshot(str(target))
    assert snap_before["readable"] is True
    assert snap_before["sha256"]

    # DENIED: kernel rejects, target SHA-256 unchanged -> WITNESS_MATCH_UNCHANGED
    res_denied = witness.action_witness(
        action_id="act-deny-1",
        target_path=str(target),
        outcome="DENIED",
        before_sha256=snap_before["sha256"],
        before_exists=True,
        kernel_verdict="HOLD",
    )
    assert res_denied["witness_verdict"] == "WITNESS_MATCH_UNCHANGED"

    # ALLOWED: target mutated, kernel SEAL + executor receipt -> WITNESS_MATCH
    target.write_text('{"seq": 1}\n', encoding="utf-8")
    snap_after = witness.capture_target_snapshot(str(target))
    res_allowed = witness.action_witness(
        action_id="act-allow-1",
        target_path=str(target),
        outcome="ALLOWED",
        before_sha256=snap_before["sha256"],
        before_exists=True,
        expected_sha256=snap_after["sha256"],
        kernel_verdict="SEAL",
        executor_receipt_id="rcpt-001",
    )
    assert res_allowed["witness_verdict"] == "WITNESS_MATCH"

    # UNVERIFIED: outside WITNESS_ROOTS -> UNVERIFIED (never PASS)
    res_unverified = witness.action_witness(
        action_id="act-unv-1",
        target_path="/etc/passwd",
        outcome="ALLOWED",
        before_sha256="deadbeef",
        kernel_verdict="SEAL",
        executor_receipt_id="rcpt-002",
    )
    assert res_unverified["witness_verdict"] == "UNVERIFIED"


def test_baseline_coverage_and_trend_gaps(tmp_path, monkeypatch):
    from frame_organ import trend

    monkeypatch.setattr(baseline, "BASELINE_FILE", str(tmp_path / "baseline.json"))
    monkeypatch.setattr(baseline, "BASELINE_DIR", str(tmp_path))
    baseline.baseline.clear()
    baseline.load_baseline()
    cov = baseline.get_baseline_coverage()
    assert cov["configured_count"] == len(config.ORGAN_PORTS)
    assert cov["missing"] == []

    pts = [
        trend.TrendPoint(timestamp="2026-11-20T00:00:00Z", epoch=1000.0, fq=1.0),
        trend.TrendPoint(timestamp="2026-11-20T00:05:00Z", epoch=1300.0, fq=1.0),
        trend.TrendPoint(timestamp="2026-11-20T01:00:00Z", epoch=4600.0, fq=0.9),
    ]
    gaps, max_gap, status = trend.analyze_trend_gaps(pts, gap_threshold_s=600.0)
    assert len(gaps) == 1
    assert max_gap == 3300.0
    assert status == "CAUTION"
