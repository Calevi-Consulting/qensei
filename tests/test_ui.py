"""UI integration tests under pytest + Playwright — every site's UI packs as browser-driven cases.

The UI counterpart to tests/test_sites.py: one parametrized test per (site, UICase), driving the
site's web UI in a REAL browser via the pytest-playwright ``page`` fixture. It is the second of the
framework's two testing approaches — REST (test_sites.py) and UI (here) — over the same SUT plugins.

Kept in the opt-in ``ui`` lane: the default ``make pytest`` excludes it (``-m "not ui"``) because a
browser is slower/heavier than the REST gate. Run it explicitly, and watch the verification LIVE:

    make test-ui                                   # headless, parallel
    make ui-watch                                  # headed + slowed-down, single browser
    poetry run pytest tests/test_ui.py --headed    # the same, directly

Site selection via QAF_SITES (as with the REST bridge); each case carries its pack tags as markers.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")  # the UI lane needs Playwright + a browser (`make install`)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import preflight as preflight_mod  # noqa: E402
from engine.case import Expect  # noqa: E402
from engine.sut import SUTConnector  # noqa: E402
from engine.ui import discover_ui_cases  # noqa: E402

ALL_SITES = ["sut/mock-shop", "sut/restful-booker"]
SITES = [s.strip() for s in os.environ.get("QAF_SITES", ",".join(ALL_SITES)).split(",") if s.strip()]


def _collect():
    params = []
    for site in SITES:
        sut = SUTConnector(str(ROOT / site))
        for case_cls in discover_ui_cases(str(sut.ui_packs_dir)):
            marks = [getattr(pytest.mark, t) for t in getattr(case_cls, "tags", ())]
            marks += [pytest.mark.ui, pytest.mark.integration]
            params.append(pytest.param(site, case_cls, id=f"{Path(site).name}::{case_cls.id}", marks=marks))
    return params


@pytest.mark.parametrize("site,case_cls", _collect())
def test_ui_pack(site, case_cls, sut_for, page):
    sut = sut_for(site)
    if not sut.ui_path:
        pytest.skip(f"{Path(site).name} declares no UI (manifest.ui.path)")
    if preflight_mod.evaluate(case_cls, sut, preflight_mod.default_registry(sut)):
        pytest.skip("unmet pre-flight requirement(s)")

    sut.isolate()  # clean state before the case (clear ephemeral bookings), as run_case does
    case, expect = case_cls(), Expect()
    try:
        case.run(page, sut.base_url + sut.ui_path, expect)
    finally:
        try:
            case.teardown(sut)
        except Exception:  # noqa: BLE001 - cleanup must never mask the assertion result
            pass
    assert expect.passed, "; ".join(f.detail for f in expect.failures) or f"{case.id} failed"
