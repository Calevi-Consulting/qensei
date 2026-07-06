"""Site integration tests under pytest + xdist — every site's regression packs as pytest cases.

This is the pytest front-end over the SAME ``RegressionCase`` packs the ``engine.run`` gate runs:
one parametrized test per (site, case), executed through ``engine.runner.run_case`` so isolate /
teardown / soft-asserts behave identically. ``pytest -n auto`` fans the cases across xdist workers;
each worker boots its own SUT (own server + own durable-state files — see conftest), so the run is
safely parallel.

Selecting a site: set ``QAF_SITES`` (comma-separated SUT dirs) to narrow which sites' packs are
collected — CI uses it to validate a single chosen site; unset collects every site. Each case also
carries its pack ``tags`` as pytest markers (plus ``integration``), so ``pytest -m smoke`` runs a lane.

(The zero-dependency ``unittest`` suite lives in ``tools/tests/``; this directory is the pytest one.)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import preflight as preflight_mod  # noqa: E402
from engine import runner  # noqa: E402
from engine.sites import gate_sites  # noqa: E402
from engine.sut import SUTConnector  # noqa: E402

# Auto-discovered from sut/*/manifest.json (in_process + has packs) — no hardcoded site list, so an
# adopter who replaces the example SUTs does not have to edit this bridge. See engine/sites.py.
ALL_SITES = gate_sites(ROOT)
SITES = [s.strip() for s in os.environ.get("QAF_SITES", ",".join(ALL_SITES)).split(",") if s.strip()]


def _collect():
    params = []
    for site in SITES:
        packs_dir = SUTConnector(str(ROOT / site)).packs_dir
        for case_cls in runner.discover_cases(str(packs_dir)):
            marks = [getattr(pytest.mark, t) for t in getattr(case_cls, "tags", ())]
            marks.append(pytest.mark.integration)
            params.append(pytest.param(site, case_cls, id=f"{Path(site).name}::{case_cls.id}", marks=marks))
    return params


@pytest.mark.parametrize("site,case_cls", _collect())
def test_pack(site, case_cls, sut_for):
    sut = sut_for(site)
    # Honor the case's pre-flight requirements (skip-or-run), exactly like the gate does.
    unmet = preflight_mod.evaluate(case_cls, sut, preflight_mod.default_registry(sut))
    if unmet:
        pytest.skip("unmet pre-flight: " + "; ".join(f"{u.key} ({u.reason})" for u in unmet))
    case, expect, error = runner.run_case(case_cls, sut)
    assert error is None, f"{case.id} errored: {error}"
    assert expect.passed, "; ".join(f.detail for f in expect.failures) or f"{case.id} failed"
