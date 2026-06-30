"""Source-clone freshness gate — don't trust a stale source when citing it.

Design + diagnostics + the review lenses read the backend SOURCE to ground their claims.
If that source is a checked-out clone of a real backend (``runtime.mode == remote``), a
stale or dirty clone means a lens could cite code that no longer matches production. This
gate checks the clone is in sync with its origin default branch before its source is trusted.

  * in_process plugin (the mock: source IS the app) -> FRESH (no-op, nothing to sync)
  * remote plugin whose source dir is a git clone   -> compare local HEAD vs origin/HEAD
        clean & in sync -> FRESH ; ahead/behind/dirty/detached -> STALE (exit 1)
  * remote plugin whose source dir is NOT a git repo -> UNKNOWN (exit 0 with a note)

This is the product-neutral half of t-800's ``tools/freshness_gate.py`` driven off the
active SUT plugin instead of a fixed ``codebase/`` layout.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _git(args, cwd):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False)


def check_freshness(sut_dir: str) -> tuple[str, str]:
    """Return ``(status, detail)`` with status FRESH | STALE | UNKNOWN."""
    d = Path(sut_dir).resolve()
    manifest = json.loads((d / "manifest.json").read_text())
    source_dir = d / manifest["source"]["path"]
    mode = manifest.get("runtime", {}).get("mode")

    if mode != "remote":
        return "FRESH", "in_process plugin — source is the app itself, nothing to sync"

    if _git(["rev-parse", "--is-inside-work-tree"], source_dir).returncode != 0:
        return "UNKNOWN", f"source dir {source_dir} is not a git clone — cannot check freshness"

    if _git(["status", "--porcelain"], source_dir).stdout.strip():
        return "STALE", "source clone has uncommitted changes (dirty)"

    _git(["fetch", "--quiet", "origin"], source_dir)
    head = _git(["rev-parse", "HEAD"], source_dir).stdout.strip()
    origin = _git(["rev-parse", "origin/HEAD"], source_dir).stdout.strip()
    if not origin:
        return "UNKNOWN", "no origin/HEAD to compare against"
    if head != origin:
        return "STALE", f"local HEAD {head[:8]} != origin/HEAD {origin[:8]} — clone is behind/ahead"
    return "FRESH", f"clone in sync with origin ({head[:8]})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="qa-framework SUT-source freshness gate")
    ap.add_argument("--sut", required=True, help="path to a SUT plugin dir")
    args = ap.parse_args(argv)
    status, detail = check_freshness(args.sut)
    print(f"  freshness-gate: {status} — {detail}")
    return 1 if status == "STALE" else 0


if __name__ == "__main__":
    sys.exit(main())
