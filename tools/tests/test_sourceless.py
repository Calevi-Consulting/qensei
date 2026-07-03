"""Sourceless-mode integration + regression tests (spec 001).

Boots the widget-api stub (a stand-in remote backend) and drives the REAL regression gate
(``engine.run.main``) against it — proving a SOURCELESS SUT (no manifest ``source``) runs its
packs against a live runtime, trips the false-green guard when unreachable, and that diagnostics
degrades to INDETERMINATE. Also guards invariant R0: source-backed SUTs are unchanged.
"""
from __future__ import annotations

import importlib.util
import threading
import unittest
from pathlib import Path

from engine import diagnostics, freshness_gate, runner
from engine.config import Settings
from engine.run import main as gate_main
from engine.sut import SUTConnector

ROOT = Path(__file__).resolve().parents[2]
WIDGET_SUT = "sut/widget-api"


def _load_stub():
    path = ROOT / WIDGET_SUT / "stub_runtime.py"
    spec = importlib.util.spec_from_file_location("widget_stub", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Stub:
    """Boot the widget-api stub on an ephemeral port; a context manager."""

    def __init__(self, buggy=False):
        self.httpd = _load_stub().make_server(buggy=buggy)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


class SourcelessMode(unittest.TestCase):
    def test_gate_passes_against_live_runtime(self):
        # AC2 (integration-boundary): the sourceless SUT's pack runs against a REAL runtime.
        with _Stub() as stub:
            rc = gate_main(["--sut", WIDGET_SUT, "--base_url", stub.url])
        self.assertEqual(rc, 0, "sourceless gate should PASS against the live stub")

    def test_false_green_guard_when_unreachable(self):
        # A closed port (a stub booted then shut down): remote + unreachable must trip the
        # false-green guard (exit 2), never a false pass.
        with _Stub() as stub:
            dead_url = stub.url
        rc = gate_main(["--sut", WIDGET_SUT, "--base_url", dead_url])
        self.assertEqual(rc, 2, "unreachable sourceless SUT must trip the false-green guard")

    def test_has_source_flags(self):
        # AC0 / AC1: widget-api is sourceless; the source-backed sites are unchanged.
        self.assertFalse(SUTConnector(str(ROOT / WIDGET_SUT)).has_source)
        for backed in ("sut/mock-shop", "sut/restful-booker"):
            self.assertTrue(SUTConnector(str(ROOT / backed)).has_source, backed)

    def test_diagnose_is_indeterminate(self):
        # AC5 / AC11: a failure on a sourceless SUT diagnoses as INDETERMINATE (contract = ticket),
        # never a guessed REAL/TEST verdict.
        cases = list(runner.discover_cases(str(ROOT / WIDGET_SUT / "packs")))
        self.assertEqual(len(cases), 1, "expected exactly the WIDGET-1 pack")
        with _Stub(buggy=True) as stub:  # buggy: created widget is "inactive" -> the case fails
            settings = Settings.load(overrides={"BASE_URL": stub.url})
            sut = SUTConnector(str(ROOT / WIDGET_SUT), settings=settings)
            sut.start()
            try:
                d = diagnostics.diagnose(cases[0], sut)
            finally:
                sut.stop()
        self.assertEqual(d["verdict"], "INDETERMINATE")
        self.assertEqual(d.get("contract_of_record"), "ticket")

    def test_freshness_skips_sourceless(self):
        # AC3 / AC13: freshness is FRESH for a sourceless SUT — its ticket/doc snapshot is in-repo.
        status, detail = freshness_gate.check_freshness(str(ROOT / WIDGET_SUT))
        self.assertEqual(status, "FRESH")
        self.assertIn("snapshot", detail)


if __name__ == "__main__":
    unittest.main()
