# deployed-rescue/ — code imported from /opt/frame (deployed tree)

Rescued 2026-10-15 under the grounding campaign: `/opt/frame` is the ONLY copy
of this code outside the live service (single point of loss).

## Layout difference (why this subdirectory exists)

- Deployed package lives at `/opt/frame/app/frame_organ/` (entry `app/`).
- This repo's source lives at `src/frame_organ/` — the deployed tree does NOT
  follow the repo layout, so these files are parked here verbatim instead of
  being merged into `src/` (that reconciliation is follow-up work, not done).

## Contents (copied verbatim from /opt/frame 2026-10-15)

| File | Status vs `src/frame_organ/` |
|------|------------------------------|
| `app/frame_organ/witness.py` | deployed-ONLY — does not exist in `src/` |
| `app/frame_organ/baseline.py` | differs from `src/` copy |
| `app/frame_organ/config.py`  | differs from `src/` copy |
| `app/frame_organ/main.py`    | differs from `src/` copy |

`/opt/frame/mcp/frame_mcp_fastmcp.py` was also diffed: identical to
`mcp/frame_mcp_fastmcp.py` in this repo (synced earlier 2026-10-15, commit
2c862e3) — nothing to rescue from `mcp/`.

Deployed tree also snapshotted independently as `ariffazil/frame-deployed`
(private) on 2026-10-15.
