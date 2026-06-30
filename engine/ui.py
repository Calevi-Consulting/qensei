"""UICase — the unit of UI (browser-driven) functional coverage.

The framework supports BOTH testing approaches over the same SUT plugin seam:

  * REST  — ``RegressionCase`` (engine/case.py): ``run(self, sut, expect)`` calls the JSON API
            through the ``SUTConnector`` (``sut.get`` / ``sut.post``). Fast, deterministic, the
            default gate.
  * UI    — ``UICase`` (this module): ``run(self, page, base_url, expect)`` drives a real browser
            (a Playwright ``page``) against the site's web UI. End-to-end through the front-end.

A ``UICase`` declares the SAME metadata a ``RegressionCase`` does (``id`` / ``spec_ref`` /
``persona`` / ``covers`` / ``tags`` / ``severity`` / ``requires``) so the DESIGN and reporting
layers treat both uniformly; only the execution surface differs (a browser page vs the REST
connector). UI packs live under ``sut/<name>/ui-packs/`` and are run by the pytest UI bridge
(tests/test_ui.py) with Playwright — kept in their own opt-in lane because a browser is slower and
heavier than the REST gate.

``run`` receives:
  * ``page``      — a Playwright ``Page`` (from pytest-playwright; honours ``--headed`` / ``--slowmo``
                    so a QA person can watch the verification live).
  * ``base_url``  — where the site's UI is served (the SUT's runtime URL + the manifest ``ui.path``).
  * ``expect``    — the same soft-assertion collector the REST cases use (engine/case.py:Expect).
"""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path


class UICase:
    id = "UNNAMED"
    title = ""
    spec_ref = None
    persona = "new_user"
    covers = []
    contract_claim = None
    tags = frozenset()
    severity = "medium"
    requires = []

    def run(self, page, base_url, expect):  # noqa: D401 - implemented by concrete UI packs
        raise NotImplementedError

    def teardown(self, sut):  # noqa: D401 - overridden by cases that create durable state
        """Best-effort cleanup of anything this case created. Default: no-op."""
        return None


def _load_module(case_file):
    case_file = Path(case_file)
    spec = importlib.util.spec_from_file_location(f"uipack_{case_file.parent.name}", case_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def discover_ui_cases(ui_packs_dir):
    """All ``UICase`` subclasses in ``ui_packs_dir/*/case.py`` (empty if the dir is absent)."""
    cases = []
    directory = Path(ui_packs_dir)
    if not directory.exists():
        return cases
    for case_file in sorted(directory.glob("*/case.py")):
        mod = _load_module(case_file)
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, UICase) and obj is not UICase:
                cases.append(obj)
    return cases
