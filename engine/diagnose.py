"""python -m engine.diagnose --sut sut/mock-shop --pack <pack-dir> [--seed-bug]

Runs ONE pack's case against the SUT and, if it fails, classifies the failure as
REAL_BUG vs TEST_BUG by reading the backend contract. Use --seed-bug to boot the
mock backend with a regression and watch the lens catch it.
"""
from __future__ import annotations

import argparse
import sys

from engine import diagnostics, runner
from engine.sut import SUTConnector


def main(argv=None):
    ap = argparse.ArgumentParser(description="Qensei failure diagnostics")
    ap.add_argument("--sut", required=True)
    ap.add_argument("--pack", required=True, help="path to a single pack dir (contains case.py)")
    ap.add_argument("--seed-bug", action="store_true")
    args = ap.parse_args(argv)

    case_cls = runner.load_pack_case(args.pack)
    sut = SUTConnector(args.sut)
    sut.start(buggy=args.seed_bug)
    try:
        d = diagnostics.diagnose(case_cls, sut)
    finally:
        sut.stop()

    diagnostics.print_diagnosis(d)
    # exit 0 — diagnosis always "succeeds"; the verdict is the payload.
    return 0


if __name__ == "__main__":
    sys.exit(main())
