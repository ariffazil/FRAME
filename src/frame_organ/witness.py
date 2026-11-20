"""FRAME 7th chamber — WITNESS: field of view over paths, consumption, claims.

Evidence only, never verdict. Every fact is derived from files and units the
agent did not author; agent prose is ingested as CLAIMS and checked against
those records, never trusted. Forged 2026-09-30 (FI-003 under F13 order) after
the decoy-fed triadic snapshot incident showed FRAME could not see which file
each consumer actually reads.

Witness classes (epistemic labels, not governance verdicts):
  TRUTH / CANONICAL / DIGEST / DECOY-FIXTURE / MISSING / EACCES / UNKNOWN
  Agreement classes: AGREE / MISTIE / STALE / CONTRADICTED / UNVERIFIABLE
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

TRUTH_HUMAN = "/var/lib/well/state.json"
DECOY_HUMAN = "/root/WELL/state.json"
SNAPSHOT_CANON = "/state/triadic_snapshot.json"
SNAPSHOT_DIGEST = "/root/WELL/state/triadic_snapshot.json"
SNAPSHOT_MAX_AGE_S = 180

# ── helpers ─────────────────────────────────────────────────────────

# ── witness reach ───────────────────────────────────────────────────
# A path outside these roots is not "absent"; it is outside the witness's
# field of view. The distinction matters: sandbox masking must never be
# reported as a contradiction.
WITNESS_ROOTS = tuple(
    p.strip()
    for p in os.getenv(
        "FRAME_WITNESS_ROOTS",
        "/opt/frame:/var/lib/frame:/var/tmp:/root/chron/data:/root/.local/share/arifos",
    ).split(":")
    if p.strip()
)


def _in_witness_reach(path: str) -> bool:
    try:
        target = os.path.abspath(path)
        return any(
            target == os.path.abspath(root)
            or target.startswith(os.path.abspath(root).rstrip("/") + "/")
            for root in WITNESS_ROOTS
        )
    except Exception:  # noqa: BLE001
        return False



def _read_json(path: str) -> dict[str, Any] | None:
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return None
    except Exception:  # noqa: BLE001 — witness must survive anything on disk
        return None


def _age_s(path: str) -> float | None:
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return None


def _classify(path: str) -> str:
    if path == TRUTH_HUMAN:
        return "TRUTH"
    if path == DECOY_HUMAN:
        return "DECOY-FIXTURE"
    if path == SNAPSHOT_CANON:
        return "CANONICAL"
    if path == SNAPSHOT_DIGEST:
        return "DIGEST"
    return "PATH"


# ── 1. PATH witness: which file does each consumer actually read? ───

# (consumer, source file, regex capturing a path literal it reads)
_CONSUMERS = [
    ("morning_briefing", "/root/scripts/morning_briefing.py",
     r'WELL_SNAPSHOT\s*=\s*Path\("([^"]+)"\)'),
    ("triadic_snapshot_writer", "/root/WELL/scripts/triadic_snapshot_writer.py",
     r'DIGEST\s*=\s*Path\("([^"]+)"\)'),
    ("well_triad_phase4_default", "/root/WELL/well_triad/phase4_tools.py",
     r'os\.environ\.get\("WELL_STATE_PATH",\s*"([^"]+)"\)'),
]

# units whose env decides whether hermetic code gets the truth path or the
# decoy default (the 2026-09-30 class-killer — regression here is reportable)
_UNITS = [
    ("triadic-snapshot.service", "WELL_STATE_PATH"),
    ("well.service", "WELL_STATE_PATH"),
]


def path_witness() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for name, src, rx in _CONSUMERS:
        row: dict[str, Any] = {"consumer": name, "source": src}
        try:
            text = Path(src).read_text()
            found = sorted(set(re.findall(rx, text)))
            row["reads"] = [{"path": p, "class": _classify(p)} for p in found]
        except FileNotFoundError:
            row["reads"] = []
            row["status"] = "SOURCE_MISSING"
        except PermissionError:
            row["reads"] = []
            row["status"] = "EACCES"
        rows.append(row)
    units = []
    for unit, var in _UNITS:
        env_val: str | None = None
        try:
            out = subprocess.run(
                ["systemctl", "show", unit, "-p", "Environment", "--value"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            m = re.search(rf"{var}=(\S+)", out)
            env_val = m.group(1) if m else None
        except Exception:  # noqa: BLE001
            env_val = None
        units.append({
            "unit": unit, "var": var, "value": env_val,
            "class": _classify(env_val) if env_val else "NOT_SET",
        })
    decoy = _read_json(DECOY_HUMAN)
    findings = []
    for r in rows:
        for read in r.get("reads", []):
            if read["class"] == "DECOY-FIXTURE" and "default" in r["consumer"]:
                findings.append(
                    f"{r['consumer']}: code default points at the fixture {read['path']} — "
                    "any runner without WELL_STATE_PATH env inherits it")
    if decoy is not None and (decoy.get("timestamp") is None
                              or decoy.get("environment") not in ("PROD", None)):
        findings.append(f"decoy sentinel live: {DECOY_HUMAN} carries "
                        f"well_score={decoy.get('well_score')} timestamp={decoy.get('timestamp')} "
                        "— it is still written by an attestation/keepalive path")
    for u in units:
        if u["class"] == "NOT_SET":
            findings.append(f"unit {u['unit']} sets no {u['var']} — hermetic consumers "
                            "on that unit fall back to code defaults")
    return {
        "witness": "paths",
        "consumers": rows,
        "units": units,
        "findings": findings,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ── 2. CONSUMER witness: do the surfaces agree with the organ? ──────


def _organ_truth() -> tuple[dict[str, Any] | None, str]:
    """Prefer the substrate file; fall back to the organ's own /health surface.
    frame is a separate principal — if /var/lib/well is out of its read reach,
    the organ HTTP surface is the legitimate witness path (same as probe)."""
    t = _read_json(TRUTH_HUMAN)
    if t is not None:
        return t, "file"
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:18083/health", timeout=5) as r:
            d = json.loads(r.read())
        fr = d.get("freshness") or {}
        return ({
            "well_score": d.get("well_score"),
            "freshness": str(fr.get("status") or "").upper(),
            "timestamp": fr.get("source_timestamp_utc"),
            "consent": None,  # not on /health — consent lines go UNVERIFIABLE
        }, "health-http")
    except Exception:  # noqa: BLE001
        return None, "unreachable"


def consumption_witness() -> dict[str, Any]:
    truth, truth_source = _organ_truth()
    canon = _read_json(SNAPSHOT_CANON)
    digest = _read_json(SNAPSHOT_DIGEST)
    comparisons: list[dict[str, Any]] = []

    def _cmp(field: str, organ: Any, consumer: Any, src: str) -> None:
        if organ is None or consumer is None:
            status = "UNVERIFIABLE"
        elif isinstance(organ, float) and isinstance(consumer, (int, float)):
            status = "AGREE" if abs(organ - consumer) <= 0.5 else "MISTIE"
        else:
            status = "AGREE" if organ == consumer else "MISTIE"
        comparisons.append({"field": field, "surface": src,
                            "organ": organ, "consumer": consumer, "status": status})

    if truth is None:
        return {"witness": "consumption", "status": "TRUTH_UNREACHABLE",
                "path": TRUTH_HUMAN, "truth_source": truth_source}
    t_bio = truth.get("biometric") or {}
    consent_block = truth.get("consent")
    t_consent = len((consent_block or {}).get("scopes", {})) if consent_block else None
    if canon:
        tri = canon.get("triadic", {})
        h = tri.get("human", {})
        _cmp("well_score", truth.get("well_score"), h.get("well_score"), "triadic.human")
        _cmp("band", truth.get("freshness"), h.get("band"), "triadic.human")
        g = tri.get("governance", {})
        organ_consent = (t_consent > 0) if t_consent is not None else None
        _cmp("consent_present", organ_consent, g.get("consent_intact"), "triadic.governance")
        _cmp("rasa", t_bio.get("rasa"), (h.get("biometric") or {}).get("rasa")
             if isinstance(h.get("biometric"), dict) else None, "triadic.human.rasa")
    else:
        comparisons.append({"field": "snapshot", "surface": SNAPSHOT_CANON,
                            "organ": None, "consumer": None, "status": "MISSING"})
    if digest:
        _cmp("well_score", truth.get("well_score"), digest.get("well_score"), "digest")
    canon_age = _age_s(SNAPSHOT_CANON)
    headline = None
    misties = [c for c in comparisons if c["status"] == "MISTIE"]
    if misties:
        headline = ("MISTIE — organ and consumer surfaces disagree; the disagreement "
                    "itself is the finding, not either value: "
                    + "; ".join(f"{m['field']} on {m['surface']}" for m in misties))
    elif canon_age is not None and canon_age > SNAPSHOT_MAX_AGE_S:
        headline = f"STALE — canonical snapshot is {canon_age:.0f}s old (writer dead?)"
    return {
        "witness": "consumption",
        "headline": headline,
        "organ_truth": {"path": TRUTH_HUMAN, "truth_source": truth_source,
                        "well_score": truth.get("well_score"),
                        "freshness": truth.get("freshness"), "timestamp": truth.get("timestamp"),
                        "consent_scopes": t_consent},
        "surfaces": {"canonical": {"path": SNAPSHOT_CANON, "age_s": canon_age},
                     "digest": {"path": SNAPSHOT_DIGEST, "present": digest is not None}},
        "comparisons": comparisons,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ── 3. CLAIM witness: mechanical check of atomic claims ─────────────



def _is_local_path(path: str) -> bool:
    """True when path names a local filesystem location, not a remote URL.

    2026-11-12 fix: os.path.abspath('https://x') collapses to <cwd>/https:/x,
    which sits inside witness root /opt/frame — URL claims masqueraded as
    in-reach files and printed CONTRADICTED on fetch failure. Scheme-detect
    first; remote surfaces are honestly UNVERIFIABLE (FRAME witnesses local
    files only).
    """
    import re as _re
    return not _re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*://", str(path or ""))


def _check_claim(claim: dict[str, Any]) -> dict[str, Any]:
    ev = claim.get("evidence") or {}
    kind = ev.get("check")
    path = ev.get("path", "")
    out = {"claim": str(claim.get("text", ""))[:200], "evidence": ev}
    if kind in ("file_exists", "file_fresh", "json_field") and not _is_local_path(path):
        out["status"] = "UNVERIFIABLE"
        out["note"] = "URL/remote surface outside FRAME file-witness reach (local files only); not a falsification"
        return out
    try:
        if kind == "file_exists":
            if not path:
                out["status"] = "CONTRADICTED"
            elif not _in_witness_reach(path):
                out["status"] = "UNVERIFIABLE"
                out["note"] = "outside witness reach; not a falsification"
            else:
                try:
                    os.stat(path)
                    out["status"] = "VERIFIED"
                except FileNotFoundError:
                    out["status"] = "CONTRADICTED"
                except PermissionError:
                    out["status"] = "EACCES"
                    out["note"] = "file exists but is unreadable by frame (witness reach boundary)"
        elif kind == "file_fresh":
            max_age = float(ev.get("max_age_seconds", 3600))
            if not path:
                out["status"] = "CONTRADICTED"
                out["observed_age_seconds"] = None
            elif not _in_witness_reach(path):
                out["status"] = "UNVERIFIABLE"
                out["note"] = "outside witness reach; not a falsification"
                out["observed_age_seconds"] = None
            else:
                try:
                    age = time.time() - os.stat(path).st_mtime
                    out["status"] = "VERIFIED" if age <= max_age else "STALE"
                    out["observed_age_seconds"] = round(age, 1)
                except FileNotFoundError:
                    out["status"] = "CONTRADICTED"
                    out["observed_age_seconds"] = None
                except PermissionError:
                    out["status"] = "EACCES"
                    out["note"] = "file exists but is unreadable by frame (witness reach boundary)"
                    out["observed_age_seconds"] = None
        elif kind == "json_field":
            if path and not _in_witness_reach(path):
                out["status"] = "UNVERIFIABLE"
                out["note"] = "outside witness reach; not a falsification"
                return out
            data = _read_json(path) if path else None
            if data is None and path and os.path.exists(path):
                # file exists but this principal cannot read it — that is a
                # witness-reach boundary, not a falsification of the claim
                out["status"] = "UNVERIFIABLE"
                out["note"] = "file exists but unreadable by frame (witness reach boundary)"
                return out
            cur: Any = data
            rest = str(ev.get("field", ""))
            while rest and isinstance(cur, dict):
                # longest-prefix key walk: registry keys contain dots
                # ("biometric.full") and must not be torn apart by naive split
                parts = rest.split(".")
                for i in range(len(parts), 0, -1):
                    key = ".".join(parts[:i])
                    if key in cur:
                        cur = cur[key]
                        rest = ".".join(parts[i:])
                        break
                else:
                    cur = None
                    break
            if rest and isinstance(cur, list):
                cur = cur[int(rest)] if rest.isdigit() and int(rest) < len(cur) else None
            out["observed"] = cur if not isinstance(cur, (dict, list)) else str(type(cur).__name__)
            if data is None:
                out["status"] = "CONTRADICTED"
            elif "equals" in ev:
                out["status"] = "VERIFIED" if cur == ev["equals"] else "CONTRADICTED"
            else:
                out["status"] = "VERIFIED" if cur is not None else "CONTRADICTED"
        elif kind == "command_exit_zero":
            # deliberately NOT executed by FRAME — separation: witness observes,
            # never runs the actor's commands. Callers supply a receipt file.
            out["status"] = "UNVERIFIABLE"
            out["note"] = "FRAME does not execute commands; supply file_fresh/json_field receipts"
        else:
            out["status"] = "UNVERIFIABLE"
            out["note"] = "no mechanical evidence supplied (pointer-free claim)"
    except PermissionError:
        out["status"] = "EACCES"
    except Exception as exc:  # noqa: BLE001
        out["status"] = "UNVERIFIABLE"
        out["note"] = str(exc)[:120]
    return out


def claims_witness(claims: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_check_claim(c) for c in claims]
    n = len(rows)
    counts = {s: sum(1 for r in rows if r["status"] == s)
              for s in ("VERIFIED", "CONTRADICTED", "UNVERIFIABLE", "STALE", "EACCES")}
    return {
        "witness": "claims",
        "claims_checked": n,
        "counts": counts,
        "rows": rows,
        "discipline_note": "action-trace evidence outranks prose (mechanical checks only); "
                           "fluency of unpointed text raises scrutiny, never certifies",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def capture_target_snapshot(target_path: str) -> dict[str, Any]:
    """Independently read a target file and return its sha256, size, and readability."""
    import hashlib

    snap: dict[str, Any] = {
        "target_path": target_path,
        "in_reach": _in_witness_reach(target_path),
        "exists": False,
        "readable": False,
        "sha256": None,
        "size": None,
        "mtime": None,
        "error": None,
    }
    if not snap["in_reach"]:
        snap["error"] = "OUT_OF_WITNESS_REACH"
        return snap
    p = Path(target_path)
    try:
        if not p.exists():
            snap["readable"] = True
            return snap
        if not p.is_file():
            snap["exists"] = True
            snap["error"] = "NOT_A_REGULAR_FILE"
            return snap
        data = p.read_bytes()
        st = p.stat()
        snap["exists"] = True
        snap["readable"] = True
        snap["sha256"] = hashlib.sha256(data).hexdigest()
        snap["size"] = len(data)
        snap["mtime"] = st.st_mtime
    except PermissionError:
        snap["exists"] = True
        snap["error"] = "EACCES"
    except Exception as exc:  # noqa: BLE001
        snap["error"] = str(exc)[:160]
    return snap


def action_witness(
    *,
    action_id: str,
    target_path: str,
    outcome: str,
    before_sha256: str | None = None,
    before_exists: bool | None = None,
    expected_sha256: str | None = None,
    kernel_verdict: str | None = None,
    executor_receipt_id: str | None = None,
) -> dict[str, Any]:
    """Independently witness a per-action staging mutation or denial.

    If target read fails (unreadable or outside WITNESS_ROOTS), witness_verdict
    is always UNVERIFIED (never PASS).
    """
    after = capture_target_snapshot(target_path)
    out_norm = str(outcome or "").strip().upper()
    kv_norm = str(kernel_verdict or "").strip().upper()

    base: dict[str, Any] = {
        "witness": "action",
        "action_id": action_id,
        "outcome_claimed": out_norm,
        "kernel_verdict": kv_norm or None,
        "executor_receipt_id": executor_receipt_id,
        "before": {
            "sha256": before_sha256,
            "exists": before_exists,
        },
        "after": after,
        "expected_sha256": expected_sha256,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if not after["in_reach"] or not after["readable"]:
        base["witness_verdict"] = "UNVERIFIED"
        base["reason"] = f"target unreadable: {after.get('error') or 'READ_FAILED'}"
        return base

    if out_norm == "ALLOWED":
        if kv_norm not in ("SEAL", "ALLOW", "APPROVED", "PERMITTED"):
            base["witness_verdict"] = "UNVERIFIED"
            base["reason"] = f"missing admissible kernel_verdict for ALLOWED ({kv_norm or 'NONE'})"
            return base
        if not executor_receipt_id:
            base["witness_verdict"] = "UNVERIFIED"
            base["reason"] = "missing executor_receipt_id for ALLOWED"
            return base
        if not after["exists"]:
            base["witness_verdict"] = "WITNESS_MISMATCH"
            base["reason"] = "target missing after ALLOWED mutation"
            return base
        if expected_sha256 is not None and after["sha256"] != expected_sha256:
            base["witness_verdict"] = "WITNESS_MISMATCH"
            base["reason"] = "after sha256 does not match expected_sha256"
            return base
        if before_sha256 is not None and after["sha256"] == before_sha256:
            base["witness_verdict"] = "WITNESS_MISMATCH"
            base["reason"] = "target sha256 unchanged after ALLOWED mutation"
            return base
        base["witness_verdict"] = "WITNESS_MATCH"
        base["reason"] = "target mutation observed and matched with kernel verdict + executor receipt"
        return base

    if out_norm == "DENIED":
        if kv_norm not in ("HOLD", "VOID", "DENIED", "REFUSED", "BLOCKED", "888_HOLD"):
            base["witness_verdict"] = "UNVERIFIED"
            base["reason"] = f"missing rejection kernel_verdict for DENIED ({kv_norm or 'NONE'})"
            return base
        if before_sha256 is None and before_exists is None:
            base["witness_verdict"] = "UNVERIFIED"
            base["reason"] = "missing before snapshot for DENIED comparison"
            return base
        if before_exists is not None and after["exists"] != before_exists:
            base["witness_verdict"] = "WITNESS_VIOLATION"
            base["reason"] = "target existence changed despite DENIED"
            return base
        if before_sha256 is not None and after["sha256"] != before_sha256:
            base["witness_verdict"] = "WITNESS_VIOLATION"
            base["reason"] = "target sha256 mutated despite DENIED"
            return base
        base["witness_verdict"] = "WITNESS_MATCH_UNCHANGED"
        base["reason"] = "kernel rejection recorded and target sha256 confirmed unchanged"
        return base

    base["witness_verdict"] = "UNVERIFIED"
    base["reason"] = f"unsupported outcome_claimed: {out_norm or 'EMPTY'}"
    return base
