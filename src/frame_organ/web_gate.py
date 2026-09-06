"""
FRAME Pre-Flight Web Gate (Fix 2)
Authority: OBSERVATIONAL_ONLY / GATEKEEPER
Before A-FORGE executes any static push or Caddy reload to arif-fazil.com,
verify /llms.txt, rsl.xml, and vault999_hash in index.html.
If missing, abort with FATAL: AGENTIC_WEB_VIOLATION.
"""

from pathlib import Path
from typing import Dict, Any, List

WEB_ROOTS = [
    Path("/var/www/html"),
    Path("/var/www/html/arif"),
]

REQUIRED_FILES = [
    "llms.txt",
    "rsl.xml",
]


def check_preflight_web_gate() -> Dict[str, Any]:
    """Inspects all web roots for required agentic discovery files and VAULT999 hashes."""
    errors: List[str] = []
    receipt: Dict[str, Any] = {
        "status": "PASS",
        "verified_roots": [],
        "checks": {},
    }

    for root in WEB_ROOTS:
        root_str = str(root)
        receipt["verified_roots"].append(root_str)
        if not root.exists():
            errors.append(f"Web root '{root}' does not exist")
            continue

        # 1. Verify required files (llms.txt, rsl.xml)
        for req_file in REQUIRED_FILES:
            file_path = root / req_file
            key = f"{root.name}/{req_file}"
            if not file_path.exists():
                errors.append(f"Missing required file: {file_path}")
                receipt["checks"][key] = "MISSING"
            elif file_path.stat().st_size == 0:
                errors.append(f"Empty required file: {file_path}")
                receipt["checks"][key] = "EMPTY"
            else:
                receipt["checks"][key] = f"OK ({file_path.stat().st_size} bytes)"

        # 2. Verify vault999_hash in index.html
        index_file = root / "index.html"
        index_key = f"{root.name}/index.html"
        if not index_file.exists():
            errors.append(f"Missing index.html at {index_file}")
            receipt["checks"][index_key] = "MISSING"
        else:
            try:
                content = index_file.read_text(encoding="utf-8")
                if "vault999_hash" not in content and "data-vault999" not in content and "SEAL-VAULT999" not in content:
                    errors.append(f"index.html at {index_file} is missing 'vault999_hash'")
                    receipt["checks"][f"{index_key}:vault999_hash"] = "MISSING"
                else:
                    receipt["checks"][f"{index_key}:vault999_hash"] = "OK"
            except Exception as e:
                errors.append(f"Error reading {index_file}: {e}")
                receipt["checks"][index_key] = f"ERROR: {e}"

    if errors:
        receipt["status"] = "FAIL"
        receipt["violation"] = "FATAL: AGENTIC_WEB_VIOLATION"
        receipt["errors"] = errors
        return receipt

    receipt["status"] = "PASS"
    receipt["message"] = "All pre-flight web gates passed"
    return receipt


def enforce_web_gate_or_abort() -> Dict[str, Any]:
    """Strict gate enforcement: raises RuntimeError with FATAL: AGENTIC_WEB_VIOLATION on failure."""
    result = check_preflight_web_gate()
    if result["status"] != "PASS":
        msg = f"FATAL: AGENTIC_WEB_VIOLATION: {'; '.join(result['errors'])}"
        raise RuntimeError(msg)
    return result


if __name__ == "__main__":
    import sys
    try:
        res = enforce_web_gate_or_abort()
        print(f"PASS: Pre-flight web gate verified ({len(res['checks'])} checks ok).")
        sys.exit(0)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
