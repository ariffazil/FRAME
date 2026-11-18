<!-- SOT-MANIFEST
federation_release: v2026.11.18
last_verified: 2026-11-18T07:29:53Z
live_commit: feat/frame-agentic-align-20261118 (synced live at /opt/frame via canon-mutate)
live_health: ok :18085 observer (9/9 chambers active; 14 organs & gateways probed: 9 healthy, 5 degraded, 0 down)
mcp_port: 18086
mcp_tools_live: 10 (frame_health, frame_probe, frame_drift, frame_baseline, frame_trend, frame_report, frame_rsi_verify, frame_behavioral_drift, frame_witness, frame_rejections)
apex_zen: A2A delegates ⊥ MCP equips ⊥ ACT mutates ⊥ arifOS governs ⊥ F13 decides
organ: FRAME
role: observer-organ (frame-organ.service + frame-mcp.service — federation drift & witness surface)
authority: OBSERVE_ONLY — evaluates contrast and records evidence, never adjudicates
license: AGPL-3.0
truth_rule: live systemctl status frame-organ.service + :18085/health + :18086/mcp tools/list beat any static count in prose
-->

> ### Canonical sync note
> `ariffazil/FRAME` is the public repository for FRAME; the live host runs `frame-organ.service` (`:18085`) and `frame-mcp.service` (`:18086/mcp`), reconciled with the private federation state plane (`ariffazil/AAA`) on `2026-11-18`.

<p align="center"><img src="docs/assets/frame-hero.png" alt="FRAME — many signals, one evidence ledger; evidence, never a verdict" width="1280"></p>

# FRAME

**Observe. Record. Witness.**

FRAME is the independent observer of the arifOS federation: it baselines organs and shared agentic services, probes live runtime state, detects drift and trends, collects unified rejection telemetry, and cross-checks consumer file paths against claims. *Measurement without a reference frame is just numbers.*

[![Observer organ · not a judge](https://img.shields.io/badge/tier-observer__organ-6b7280.svg)](#role-invariant)
[![Health probe :18085](https://img.shields.io/badge/health-probe_--_18085-6ea8fe.svg)](http://127.0.0.1:18085/health)
[![MCP :18086 · 10 tools](https://img.shields.io/badge/MCP-%3A18086%2Fmcp%20(10%20tools)-4fd1c5.svg)](#mcp-surface-18086mcp)
[![Authority: OBSERVE_ONLY](https://img.shields.io/badge/authority-OBSERVE__ONLY-amber.svg)](#role-invariant)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](./LICENSE)

> ### Role invariant
> **Its output is evidence, never a verdict.** FRAME observes from outside and reports; it never adjudicates, never executes mutations, and never rewrites VAULT999 (read-only witness checks only).
> Judgment belongs to [arifOS](https://github.com/ariffazil/arifOS) and execution belongs to [A-FORGE](https://github.com/ariffazil/A-FORGE).
> *Authority ceiling:* `OBSERVE_ONLY` — every `/frame/drift`, `/frame/alert`, `/frame/report`, `/frame/rejections`, and `/frame/witness/*` response stamps `authority="OBSERVATIONAL_ONLY"` and `verdict_source=null`.

## What works today
*(measured `2026-11-18T07:29:53Z` against live `frame-organ.service` `:18085` and `frame-mcp.service` `:18086`)*

- **Live observer at `:18085`** — `/health` reports `status: ok`, version `1.0.0`, **9/9 chambers active** (`baseline` · `probe` · `compare` · `trend` · `alert` · `report` · `rsi_verify` · `rejection` · `witness`).
- **Aligned 14-target federation probe** (`/frame/probe`) — tracks core organs (`arifos`, `aforge`, `aforge_mcp`, `geox`, `wealth`, `well`, `aaa`, `signal`, `arifflow`, `fed`, `hermes`, `chron`) plus shared model & agentic-tool gateways (`litellm` via `/health/liveliness`, `agentic_tools` `:18430`). Retired `flame: 18901` is decommissioned.
- **Coherent status partitioning (`healthy + degraded + down == total`)** — reachable HTTP 200 endpoints declaring `"status": "degraded"` or `"degraded_mode": true` count as `degraded`, never falsely `healthy`. Live probe observed `14` targets (`9` healthy, `5` degraded, `0` down in `383.77 ms`).
- **FastMCP surface at `:18086/mcp`** (`frame-mcp.service`, `frame-mcp` `2026.11.18`) — serves **10 read-only annotated tools** (`frame_health`, `frame_probe`, `frame_drift`, `frame_baseline`, `frame_trend`, `frame_report`, `frame_rsi_verify`, `frame_behavioral_drift`, `frame_witness`, `frame_rejections`).
- **Alert & latency drift hardening** — `compare.py` enforces a `max(baseline * 3, 250.0) ms` jitter floor; `alert.py` keys 24h suppression on verdict state (`DRIFT_INCIDENT_<VERDICT>`).
- **Hermetic test suite** (`tests/test_frame_organ.py`) — covers topology alignment, `fed` vs `litellm` health paths, degraded coherence, latency floor, FastAPI routes, and 10-tool MCP annotations.
- **CI governance** — Dependabot `uv` ecosystem + `uv lock --check` & `uv sync --frozen` invariant workflow + constitutional-package denylist on auto-merge.

## What is not yet proven

- **Drift-detection accuracy** — no measured false-positive / false-negative benchmark against synthetic fault injection beyond unit tests; no external audit of `compare.py` signals.
- **Alert escalation delivery rate** — `escalate_drift` targets local SIGNAL (`:18084`); end-to-end operator delivery rates are tracked on SIGNAL, not inside FRAME.
- **Baseline refresh cadence** — `/var/lib/frame/baseline.json` holds `10` persisted baseline entries (`established_at: 2026-08-06T09:57:02Z`); newly added surfaces (`aforge_mcp`, `hermes`, `chron`, `litellm`, `agentic_tools`) return `[]` drift until persisted via `POST /frame/baseline/{organ}` (`baseline_stale: true` after 90 days).
- **Public ingress** — `:18085` and `:18086` bind loopback (`127.0.0.1`) for local agents and federation health checks (`Public MCP: —`).

## 30-second proof

```bash
curl -s http://127.0.0.1:18085/health
curl -s http://127.0.0.1:18085/frame/probe | jq '{total_organs, healthy_organs, degraded_organs, down_organs}'
```

Observed output (`2026-11-18T07:29:53Z`):

```json
{"status":"ok","organ":"frame","port":18085,"version":"1.0.0",
 "baseline_organs":10,"baseline_established":"2026-08-06T09:57:02Z",
 "chambers":{"baseline":"active","probe":"active","compare":"active","trend":"active","alert":"active","report":"active","rsi_verify":"active","rejection":"active","witness":"active"}}
```

```json
{"total_organs": 14, "healthy_organs": 9, "degraded_organs": 5, "down_organs": 0}
```

Read-only. Operator surfaces: `make health` · `make probe` · `systemctl status frame-organ.service frame-mcp.service`.

## What FRAME does

1. **Baseline** — hold expected-state metrics (`/frame/baseline`).
2. **Probe & compare** — sample all 14 federation organs & gateways and compute drift vectors (`/frame/probe`, `/frame/drift`).
3. **Trend & RSI verify** — track time series and enforce monotonic log integrity (`/frame/trend`, `/frame/rsi-verify`).
4. **Alert & report** — suppress noisy duplicates and emit structured health briefs (`/frame/alert`, `/frame/report`).
5. **Witness & rejections** — compare consumer paths vs truth files, verify atomic file/JSON claims, and aggregate rejection telemetry (`/frame/witness/*`, `/frame/rejections/*`).

## MCP Surface (`:18086/mcp`)

| Tool | Chamber / Source | Read-Only | Purpose |
|---|---|---|---|
| `frame_health` | `/health` | Yes | Chamber readiness & version |
| `frame_probe` | `/frame/probe` | Yes | Live 14-target organ & gateway probe |
| `frame_drift` | `/frame/drift` | Yes | Diff live probes against baselines |
| `frame_baseline` | `/frame/baseline` | Yes | Read baseline reference metrics |
| `frame_trend` | `/frame/trend` | Yes | FQ, up-count, and latency trend series |
| `frame_report` | `/frame/report/{period}` | Yes | Daily/weekly health brief |
| `frame_rsi_verify` | `/frame/rsi-verify` | Yes | Trend log monotonicity guard |
| `frame_behavioral_drift` | in-process metrics | Yes | Session-level agent behavioral drift |
| `frame_witness` | `/frame/witness/{scope}` | Yes | Consumer file-path & truth agreement witness |
| `frame_rejections` | `/frame/rejections*` | Yes | Unified organ rejection telemetry |

## Current verified state

**Observed at `2026-11-18T07:29:53Z`** — method: `curl -s http://127.0.0.1:18085/health`, `/frame/probe`, and MCP `tools/list` on `:18086/mcp`.

| Fact | Value |
|---|---|
| HTTP Service | `ok` · `frame-organ.service` (`127.0.0.1:18085`) · version `1.0.0` |
| MCP Service | `active` · `frame-mcp.service` (`127.0.0.1:18086/mcp`, FastMCP `2026.11.18`) · `10` read-only tools |
| Chambers | `9/9` active (`baseline`, `probe`, `compare`, `trend`, `alert`, `report`, `rsi_verify`, `rejection`, `witness`) + `/frame/gate/web-preflight` |
| Tracked Surfaces | `14` (`9` healthy, `5` degraded fail-closed, `0` down at sample time; `383.77 ms`) |
| Mutations performed | `0` — `OBSERVE_ONLY`; evidence only |

Dynamic state is generated by probe. **If this section conflicts with the live endpoint, the endpoint wins.**

## Development

```bash
uv sync --frozen
PYTHONPATH=src pytest -v tests/
```

- **Runtime:** `/opt/frame/app` (`frame-organ.service`) and `/opt/frame/mcp/frame_mcp_fastmcp.py` (`frame-mcp.service`), Python 3.13+.
- **Operator surface:** `Makefile` — `install` · `deploy` · `health` · `probe` · `clean`.
- **Logs:** `journalctl -u frame-organ.service -u frame-mcp.service`.
- **CI:** `.github/workflows/` — `dependabot-ci.yml`, `ci-uv-lock-invariant.yml`, `auto-merge-dependabot.yml`.

## License & federation identity

GNU AGPL-3.0 — arifOS Federation. Sovereign: **Muhammad Arif bin Fazil** (F13 SOVEREIGN). *DITEMPA BUKAN DIBERI — Truth must cool before it rules.*

<!-- FEDERATION-STANDARD v2026-11-18 START :: agentic alignment :: source: live probes + codebase -->
## Federation Identity
| Field | Value |
|---|---|
| Organ | `frame` · CORE · federation_measurement |
| Ports | HTTP `18085` · MCP `18086` |
| Units | `frame-organ.service` · `frame-mcp.service` |
| Authority ceiling | `OBSERVE_ONLY` |
| Live (probe `2026-11-18T07:29Z`) | UP (`14` targets probed; `9/9` chambers active; `10` MCP tools) |
| Public MCP | — (loopback `:18086/mcp`) |
| Machine claims | [`claims.json`](./claims.json) |
<!-- FEDERATION-STANDARD v2026-11-18 END -->

---

## External Footprint & Discovery

FRAME is the passive observer and drift-detection witness organ of the arifOS federation.

- **Discoverable:** YES (GitHub repository)
- **Authority Ceiling:** `OBSERVE_ONLY` (evidence and contrast only — never mutates terminal states)
- **Inspectable & Forkable:** YES
- **Independent Validation:** NOT YET ESTABLISHED

Canonical Witness Ledger: [EXTERNAL_WITNESS_LEDGER.md](https://github.com/ariffazil/arifOS/blob/main/docs/EXTERNAL_WITNESS_LEDGER.md)
