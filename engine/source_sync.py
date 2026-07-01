"""SUT source provisioning — keep a local clone of a SUT's real source in sync.

Design + diagnostics + the review lenses read the backend SOURCE (``ROUTES`` /
``BUSINESS_RULES``, plus the code the lenses cite) from ``manifest.source.path``. For the
example SUTs that dir holds a committed in-repo mock. For a REAL backend, ``manifest.source``
instead declares where the source lives upstream, and this module materialises / refreshes a
local clone there so every read is against current code:

    "source": {
        "path": "source",                 # where the clone lands (gitignored for real SUTs)
        "repo": "https://.../backend.git", # upstream git URL
        "ref":  "main",                   # branch | tag | sha (optional; default: default branch)
        "depth": 1                        # shallow depth (optional; 0 = full clone)
    }

Semantics (a gitignored per-SUT clone — product-neutral):
  * no ``source.repo``                          -> SKIP: source is in-repo (mock/contract).
  * ``source.path`` absent/empty                -> clone ``repo`` (shallow) and check out ``ref``.
  * ``source.path`` is ITS OWN git clone        -> fetch ``ref`` and hard-reset to it (idempotent).
  * ``source.path`` non-empty, NOT its own clone -> ERROR: refuse to clobber it.

The "its own clone" test compares ``git -C <path> rev-parse --show-toplevel`` to ``path``:
a SUT lives INSIDE the Qensei repo, so a naive ``--is-inside-work-tree`` would report the
PARENT repo and we could fetch/reset the wrong tree. The toplevel check avoids that.

Run:  ``python -m engine.source_sync --sut sut/<name>``  (or ``make sync-source SUT=sut/<name>``).
It is the provider the offline ``engine/freshness_gate.py`` assumes: sync makes the clone
FRESH; the gate then trusts it. This is a network-touching, assistant-driven step — it is NOT
part of the deterministic offline gate (``make test``).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _git(args, cwd=None):
    """Run a git command, capturing output; never raises (callers inspect returncode)."""
    prefix = ["-C", str(cwd)] if cwd else []
    return subprocess.run(["git", *prefix, *args], capture_output=True, text=True, check=False)


def _is_own_clone(path: Path) -> bool:
    """True iff ``path`` is the top of its OWN git worktree (not the parent Qensei repo)."""
    if not path.is_dir():
        return False
    r = _git(["rev-parse", "--show-toplevel"], path)
    return r.returncode == 0 and Path(r.stdout.strip()).resolve() == path.resolve()


def _short_head(path: Path) -> str:
    return _git(["rev-parse", "--short", "HEAD"], path).stdout.strip()


def sync(sut_dir: str) -> tuple[str, str]:
    """Ensure ``source.path`` is a clone of ``source.repo`` at ``ref``.

    Returns ``(status, detail)`` with status SKIP | SYNCED | ERROR.
    """
    d = Path(sut_dir).resolve()
    manifest = json.loads((d / "manifest.json").read_text())
    source = manifest.get("source", {})
    repo = source.get("repo")
    path = d / source["path"]

    if not repo:
        return "SKIP", "in-repo source (no source.repo) — nothing to clone"

    ref = source.get("ref")
    depth = source.get("depth", 1)

    # (1) Existing clone -> refresh to the requested ref (uniform for branch/tag/sha).
    if _is_own_clone(path):
        fetch = ["fetch", "--tags"] + (["--depth", str(depth)] if depth else []) + ["origin"] + ([ref] if ref else [])
        r = _git(fetch, path)
        if r.returncode != 0:
            return "ERROR", f"git fetch failed: {r.stderr.strip()}"
        target = "FETCH_HEAD" if ref else "origin/HEAD"
        r = _git(["reset", "--hard", target], path)
        if r.returncode != 0:
            return "ERROR", f"git reset failed: {r.stderr.strip()}"
        return "SYNCED", f"updated clone to {_short_head(path)} ({ref or 'default branch'})"

    # (2) Non-empty, not-our-clone -> refuse to clobber committed/local source.
    if path.exists() and any(path.iterdir()):
        return "ERROR", (f"{path} exists, is non-empty and is not its own git clone — refusing "
                         f"to clobber committed/local source (remove it first to provision a clone)")

    # (3) Fresh clone (shallow, at ref). Fall back to full clone + checkout for a sha ref.
    clone = ["clone"] + (["--depth", str(depth)] if depth else []) + (["--branch", ref] if ref else []) + [repo, str(path)]
    r = _git(clone)
    if r.returncode != 0 and ref:
        shutil.rmtree(path, ignore_errors=True)
        r = _git(["clone", repo, str(path)])
        if r.returncode == 0:
            r = _git(["checkout", ref], path)
    if r.returncode != 0:
        return "ERROR", f"git clone failed: {r.stderr.strip()}"
    return "SYNCED", f"cloned {repo} @ {_short_head(path)} ({ref or 'default branch'})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Qensei SUT source provisioning (clone/refresh)")
    ap.add_argument("--sut", required=True, help="path to a SUT plugin dir")
    args = ap.parse_args(argv)
    status, detail = sync(args.sut)
    print(f"  source-sync: {status} — {detail}")
    return 1 if status == "ERROR" else 0


if __name__ == "__main__":
    sys.exit(main())
