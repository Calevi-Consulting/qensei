"""python -m engine.run --sut sut/mock-shop [options]

Runs the regression gate: packs under --packs against the SUT. Exit code is non-zero if
any case fails OR a false-green precondition trips (no cases ran / all skipped / SUT
unreachable / credentials unresolved), so CI can gate on it.

Options:
  --env NAME        select an environment from manifest["env"] (or set QAF_ENV)
  --base_url URL    override the base_url outright (or set QAF_BASE_URL)
  --select EXPR     run only cases matching a tag expression, e.g. "smoke and not slow"
  --preflight MODE  "partial" (skip unmet-requirement cases) | "block" (fail them)
  --report PATH     also write a machine-readable report (.xml = JUnit, .json = JSON)
  --seed-bug        boot the mock backend with a seeded regression (demo)
"""
from __future__ import annotations

import argparse
import sys

from engine import report as report_mod
from engine import runner
from engine.config import Settings
from engine.credentials import CredentialError
from engine.sut import SUTConnector


def _precheck(sut, results) -> str | None:
    """Return a reason string if the run is a FALSE GREEN (else None)."""
    if not results:
        return "no cases discovered/selected — an empty run must not pass"
    if all(r[3] == "SKIP" for r in results):
        return "every case skipped (unmet pre-flight) — nothing was actually verified"
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="qa-framework regression gate")
    ap.add_argument("--sut", required=True, help="path to a SUT plugin dir (e.g. sut/mock-shop)")
    ap.add_argument("--packs", default=None,
                    help="directory of regression packs (default: the SUT's own packs dir)")
    ap.add_argument("--env", help="environment name from manifest['env']")
    ap.add_argument("--base_url", help="override base_url outright")
    ap.add_argument("--select", help='tag expression, e.g. "smoke and not slow"')
    ap.add_argument("--preflight", choices=["partial", "block"], default="partial")
    ap.add_argument("--report", help="write a machine-readable report (.xml JUnit / .json)")
    ap.add_argument("--seed-bug", action="store_true", help="boot the mock with a seeded regression")
    args = ap.parse_args(argv)

    settings = Settings.load(overrides={"ENV": args.env, "BASE_URL": args.base_url, "PREFLIGHT": args.preflight})
    try:
        sut = SUTConnector(args.sut, settings=settings)
    except CredentialError as e:
        print(f"\n  GATE FALSE-GREEN GUARD: credentials did not resolve — {e}\n", file=sys.stderr)
        return 2

    packs = args.packs or str(sut.packs_dir)  # default to THIS site's packs (self-contained)
    sut.start(buggy=args.seed_bug)
    try:
        if sut.runtime_mode() == "remote" and not sut.reachable():
            print(f"\n  GATE FALSE-GREEN GUARD: SUT unreachable @ {sut.base_url}\n", file=sys.stderr)
            return 2
        results = runner.run_packs(sut, packs, select=args.select, preflight=settings.preflight)
    finally:
        sut.stop()

    if args.report:
        report_mod.write_report(results, args.report, suite_name=f"{sut.name}-{settings.env or 'default'}")
        print(f"  report written: {args.report}")

    reason = _precheck(sut, results)
    if reason:
        print(f"\n  GATE FALSE-GREEN GUARD: {reason}\n", file=sys.stderr)
        return 2

    failed = [r for r in results if r[3] == "FAIL"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
