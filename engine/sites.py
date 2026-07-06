"""Discover the SUT sites the integration gate runs — so the pytest bridges and the CI matrices
AUTO-ADAPT to whatever plugins live under ``sut/`` instead of a hardcoded ``ALL_SITES`` list.

This is what lets an adopter DELETE the shipped example SUTs (mock-shop / restful-booker / widget-api)
and drop in their own without editing the test bridges or CI: the engine and gates already discover
packs by glob (``runner.py`` / ``ui.py`` / ``coverage_lint.py`` / ``fidelity_lint.py``); this closes
the same gap for ``tests/test_sites.py``, ``tests/test_ui.py``, and both CI ``select-sites`` matrices.

A site is **gate-runnable** when it has at least one pack AND its default runtime boots offline
(``runtime.mode == "in_process"``). A remote / sourceless SUT (e.g. ``widget-api``, or
``restful-booker`` under ``--env live``) needs live creds/env, so it is excluded from the default
offline gate — run it explicitly via ``QAF_SITES=sut/<name>`` (+ ``--env``). This reproduces the
previously-hardcoded set exactly while adapting to any new plugin.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path


def gate_sites(root: str | Path = ".") -> list[str]:
    """The ``sut/<name>`` dirs the default offline gate runs (in_process + at least one pack)."""
    root = Path(root)
    sites: list[str] = []
    for manifest_path in sorted(glob.glob(str(root / "sut" / "*" / "manifest.json"))):
        sut_dir = Path(manifest_path).parent
        try:
            manifest = json.loads(Path(manifest_path).read_text())
        except (OSError, ValueError):
            continue
        if manifest.get("runtime", {}).get("mode") != "in_process":
            continue  # remote / sourceless: needs live creds/env — not the default offline gate
        packs_dir = sut_dir / manifest.get("tests", {}).get("packs", "packs")
        if not sorted(packs_dir.glob("*/case.py")):
            continue  # no packs to run
        sites.append(f"sut/{sut_dir.name}")
    return sites


def matrix(sites: list[str]) -> dict:
    """The GitHub/GitLab ``select-sites`` matrix shape for a list of ``sut/<name>`` dirs."""
    return {"include": [{"sut": s, "site": s.split("/", 1)[1]} for s in sites]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="List the SUT sites the integration gate runs")
    ap.add_argument("--matrix", action="store_true",
                    help="emit the CI select-sites matrix JSON instead of one site per line")
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    args = ap.parse_args(argv)
    sites = gate_sites(args.root)
    if args.matrix:
        print(json.dumps(matrix(sites)))
    else:
        for site in sites:
            print(site)
    return 0


if __name__ == "__main__":
    sys.exit(main())
