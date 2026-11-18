# Changelog — FRAME (Observer)

All notable changes to the FRAME organ.

## [2026.11.18] — Agentic System Alignment & Live Reconciliation

### Added
- Tracked federation topology aligned to 14 live surfaces (`arifos`, `aforge`, `aforge_mcp`, `geox`, `wealth`, `well`, `aaa`, `signal`, `arifflow`, `fed`, `hermes`, `chron`, `litellm`, `agentic_tools`).
- Added `frame_witness` and `frame_rejections` read-only MCP tools in `mcp/frame_mcp_fastmcp.py` (8 → 10 annotated tools).
- Added hermetic unit and contract test suite in `tests/test_frame_organ.py`.

### Fixed
- Reconciled live fixes from deployed `frame_organ`: retired `flame: 18901`, `compare.py` 250ms latency floor, `alert.py` verdict-level suppression key, and `healthy + degraded + down == total` conservation invariant in `probe.py`.
- Fixed `HEALTH_PATH_OVERRIDES` in `probe.py` so `litellm` (`:4000`) probes `/health/liveliness` while `fed` (`:7074`) probes `/health` cleanly instead of 404.

## [2026.08.26] — Consolidation

### Changed
- FRAME consolidated into AAA state plane
- ARCHIVED notice published
