"""python -m engine.run --sut sut/mock-shop [--packs packs] [--seed-bug]

Runs the regression gate: every pack under --packs against the SUT. Exit code is
non-zero if any case fails (so CI can gate on it).
"""
from __future__ import annotations

import argparse
import sys

from engine import runner
from engine.sut import SUTConnector


def main(argv=None):
    ap = argparse.ArgumentParser(description="qa-framework regression gate")
    ap.add_argument("--sut", required=True, help="path to a SUT plugin dir (e.g. sut/mock-shop)")
    ap.add_argument("--packs", default="packs", help="directory of regression packs")
    ap.add_argument("--seed-bug", action="store_true", help="boot the mock backend with a seeded regression")
    args = ap.parse_args(argv)

    sut = SUTConnector(args.sut)
    sut.start(buggy=args.seed_bug)
    try:
        results = runner.run_packs(sut, args.packs)
    finally:
        sut.stop()

    failed = [r for r in results if not r[-1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
