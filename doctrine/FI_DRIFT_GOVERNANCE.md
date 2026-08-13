# FI Drift Governance Schema v1

> **Date:** 2026-08-11  
> **Owner:** FRAME (`/root/FRAME`)  
> **Registrar:** AAA (`/root/AAA`)  
> **Status:** CANON  
> **Canonical URL:** `/root/FRAME/doctrine/FI_DRIFT_GOVERNANCE.md`
> **Verdict:** SEALED with F13 Ratification

---

## 1. Purpose

This schema defines the measurement framework for tracking drift in Federated Intelligence (FI) cards across the federation. It is **not** a constitutional authority document — that belongs to arifOS kernel and VAULT999. Rather, this is a **measurement canon** owned by FRAME's observation chambers.

> **DRIFT ≠ GOVERNANCE.**  
> "Drift governance" sounds like judgment authority. The correct scope is **FI Drift Measurement** — observing variance against baseline, not making verdicts. Verdicts belong to arifOS; measurements belong to FRAME.

---

## 2. Scope: Six Chamber Mapping

Each FI drift field maps exactly to one FRAME chamber from `organs.yaml`:

| Field Category | FRAME Chamber | Responsible Organ | Output Type |
|----------------|---------------|-------------------|-------------|
| `pinned_version`, `latest_upstream` | Chamber 1 — baseline | Establish reference state | Static config |
| `drift_scan.method`, `frequency` | Chamber 2 — probe | Live measurement schedule | Configurable policy |
| `drift_tolerance`, `threshold > 0.20` | Chamber 3 — compare | Variance vs baseline | Threshold gate |
| `version_drift_window`, monotonic divergence | Chamber 4 — trend | Directional pattern detection | Trend signal |
| `drift_policy.{warning, critical, revoke}` | Chamber 5 — alert | Threshold breach signaling | Alert trigger |
| `audit_trail`, `last_audit_at` | Chamber 6 — report | Accountability logging | Immutable ledger |

**Proof of alignment:** A registry-only schema would only use Chamber 6. A full measurement framework uses all six chambers. This schema uses all six. ✅

---

## 3. Authority Boundaries (Do Not Cross)

| Concern | Owner | Forbidden Domain | Evidence Class |
|---------|-------|------------------|----------------|
| Identity registration | AAA (`AGENTS_UNIFIED.yaml`) | Do not store drift data | Registry metadata |
| Drift measurement | FRAME (`doctrine/`) | Do not make verdicts | Observation (OBS) |
| Model routing | FED (`fed_router.py`) | Do not judge architecture | Advisory (ADVISORY_ONLY) |
| Execution | A-FORGE (:7071) | Do not measure metabolism | Execute-after-seal |
| Constitutional verdict | arifOS (:8088) | Do not own measurement channels | Judgment (JUDGE_ONLY) |
| Metabolism monitoring | arifFlow (:7073) | Do not route execution | Metabolize (METABOLISM) |

---

## 4. FI Card Integration (Reference Pattern Only)

The FI agent-card.json contains **no inline drift block**. Instead, it stores a reference path to FRAME's canonical baseline storage:

```json
{
  "fi_slot": "FI-003",
  "identity": { ... Part 1 ... },
  "capabilities": { ... Part 2 ... },
  "routing": { ... Part 3 ... },
  "drift_governance_ref": {
    "schema": "FI_DRIFT_GOVERNANCE::v1",
    "schema_path": "/root/FRAME/doctrine/FI_DRIFT_GOVERNANCE.md",
    "baseline_path": "/root/FRAME/data/fi_baselines/FI-003.jsonl",
    "drift_receipts_path": "/root/forge_work/frame-drift-FI-003.jsonl",
    "last_audit_at": "<ISO 8601>",
    "owned_by": "FRAME",
    "registered_by": "AAA"
  }
}
```

**Why reference, not block?**
- Baseline can evolve without re-registering identity
- Drift receipts are append-only (never mutate card)
- Single source of truth per concern (avoids DRIFT)
- CARD becomes lightweight (meets F4 CLARITY requirement)

---

## 5. Data Plane Storage Locations

| Resource | Path | Access Control | Update Policy |
|----------|------|----------------|---------------|
| **Schema definition** | `/root/FRAME/doctrine/FI_DRIFT_GOVERNANCE.md` | F13 ratification required | Change via commit + seal |
| **Per-FI baselines** | `/root/FRAME/data/fi_baselines/{fi_slot}.jsonl` | Write-once-read-many | Append-only (never overwrite) |
| **Drift receipts** | `/root/forge_work/frame-drift-{fi_slot}.jsonl` | WRITE during scan, READ always | Appended on every drift event |
| **Audit log** | `/root/forge_work/meta/mcp-audit.jsonl` | Root write, agent read | Appended chronologically |

---

## 6. Alignment to Canonical Organs

The schema explicitly references the authoritative definitions from `organs.yaml`:

| Organ | Line Range | Definition |
|-------|------------|------------|
| **FRAME** | Lines 337–386 | "Federation Reference & Assessment Measurement Engine" - owns institutional_baseline, organ_probe, drift_detection, trend_analysis, threshold_alerting, institutional_reporting |
| **FLAME** | Lines 489–506 | "Free-tier inference mesh" - answers cheap tool meaning; never seals |
| **FED** | Lines 489–506 | "Model route advisor" - answers WHERE to call; does not call; not an organ |
| **arifOS** | Lines 27–67 | "Governance kernel" - judges constitutionality (F1-F13), never measures drift |
| **A-FORGE** | Lines 68–99 | "Execution actuator" - applies mutations after seal, never judges |

---

## 7. Integration Workflow (Helix Pattern)

The FI drift workflow follows the helix pattern identified in EUREKA-T-02:

```
STEP 1: Inner Loop (Per Task Request)
├─ FLAME pre-flight verification (RM0 free tier)
├─ FED model routing advisory
├─ A-FORGE bounded mutation
├─ arifOS constitutional verdict
└─ arif_seal → VAULT999 hash-chain append

STEP 2: Outer Loop (Per Receipt Window)
├─ arifFlow metabolizes receipts into FQ pulse
├─ If FQ < 0.5 (STUCK): HOLD non-critical execute
├─ If FQ > 10 (OVERHEAT): THROTTLE execute, force verify
└─ Store receipt to /var/lib/arifflow/receipts.jsonl

STEP 3: Helix Coupling (Causal Feedback)
├─ FRAME measures drift against baseline (Chamber 1–6)
├─ If drift > threshold: trigger re-audit (Chamber 5 alert)
├─ Re-audit result feeds carry_forward.json for next session
└─ Next inner loop runs in DIFFERENT substrate context
```

**Critical Insight:** Each cycle evolves the substrate because outer loop output (drift signal) gates inner loop conditions (re-audit triggers). This is **helix**, not **loop** — different conditions each iteration.

---

## 8. Implementation Notes (Not Authorization)

- **DO NOT modify** `fi_baselines/*.jsonl` files directly — they must remain append-only
- **DO NOT delete** old drift receipts — they are audit trail for future re-probing
- **DO cache** FRAME channel results in memory for 15-minute TTL (per arifFlow caching doctrine)
- **DO NOT assume** `pinned_version` = canonical release — it's the last known working version, subject to drift
- **DO validate** schema changes against the six-chamber map before committing

---

## 9. References

- [`organs.yaml`](/root/AAA/federation/organs.yaml) — live machine topology SOT
- [`FI_INTEGRATION_ARCHITECTURE.md`](/root/AAA/canon/FI_INTEGRATION_ARCHITECTURE.md) — single-page canon (approved)
- [`EUREKA-T-02-seven-verbs-helix.md`](/root/AAA/canon/EUREKA-T-02-seven-verbs-helix.md) — seven verbs doctrine (sealed)
- [`arifFLOW_FQ_SCALE_STANDARD.md`](/root/arifOS/docs/FQ_SCALE_STANDARD.md) — FQ gate thresholds
- [`arifFlow_DAEMON_PROTOCOL.md`](/root/arifFlow/ARIFLOW_KERNEL_CANON.md) — daemon ingest protocol

---

## 10. Ratification Status

| Step | Status | Action Required |
|------|--------|-----------------|
| Schema drafted | ✅ DONE | N/A |
| Content review | ✅ DONE | Arif reviewed and approved |
| F13 ratification | ✅ RATIFIED | This file is now canon |
| Write to canon path | ✅ DONE | Written to `/root/FRAME/doctrine/FI_DRIFT_GOVERNANCE.md` |
| Register in FI cards | ⏳ PENDING | After P3 executes |

---

*Forged: 2026-08-11 · CANON SEALED with F13 Ratification*
*DITEMPA BUKAN DIBERI ⚒️*
