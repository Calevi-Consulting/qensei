"""Zero-dependency unittest coverage for seeded-run provenance (issue #41).

`--seed-bug` injects a fault so the framework can demonstrate REAL_BUG detection. The resulting red is
otherwise identical to a genuine regression — same exit 1, same failing case, same report — so the run
and its artifact must SAY they were seeded. These pins cover the three places that can lie about it:
the connector (did seeding actually apply?), the report (does the artifact declare it?), and the gate
end-to-end (does a real invocation stamp a real artifact?).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from engine import report as report_mod
from engine import run as run_mod
from engine.sut import SUTConnector

ROOT = Path(__file__).resolve().parents[2]
MOCK_SHOP = str(ROOT / "sut" / "mock-shop")


class _Case:
    id = "X-1"
    title = "a case"
    persona = "new_user"


def _results(status="PASS"):
    return [(_Case(), None, None, status)]


class ConnectorSeeded(unittest.TestCase):
    def test_false_before_start(self):
        self.assertFalse(SUTConnector(MOCK_SHOP).seeded)

    def test_in_process_started_clean_is_not_seeded(self):
        sut = SUTConnector(MOCK_SHOP)
        sut.start(buggy=False)
        try:
            self.assertFalse(sut.seeded)
        finally:
            sut.stop()

    def test_in_process_started_buggy_is_seeded(self):
        sut = SUTConnector(MOCK_SHOP)
        sut.start(buggy=True)
        try:
            self.assertTrue(sut.seeded)
        finally:
            sut.stop()

    def test_remote_is_never_stamped_seeded(self):
        """A remote runtime has no factory, so `buggy` is dropped. Stamping it seeded would be a
        marker that is wrong — worse than none."""
        sut = SUTConnector(str(ROOT / "sut" / "widget-api"))
        sut._base_url = "http://127.0.0.1:9"  # remote start() only checks a base_url is resolved
        sut.start(buggy=True)
        try:
            self.assertEqual(sut.runtime_mode(), "remote")
            self.assertFalse(sut.seeded)
        finally:
            sut.stop()


class ReportProvenance(unittest.TestCase):
    def test_junit_declares_seeded_true(self):
        xml = report_mod.to_junit(_results(), seeded=True)
        self.assertIn('<property name="qensei.seeded" value="true"/>', xml)

    def test_junit_declares_seeded_false_rather_than_omitting_it(self):
        """An absent marker is ambiguous between "not seeded" and "written before the field existed"."""
        xml = report_mod.to_junit(_results())
        self.assertIn('<property name="qensei.seeded" value="false"/>', xml)

    def test_json_declares_seeded(self):
        self.assertTrue(json.loads(report_mod.to_json(_results(), seeded=True))["seeded"])
        self.assertFalse(json.loads(report_mod.to_json(_results()))["seeded"])

    def test_write_report_carries_it_to_both_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            xml, js = Path(tmp) / "r.xml", Path(tmp) / "r.json"
            report_mod.write_report(_results(), str(xml), seeded=True)
            report_mod.write_report(_results(), str(js), seeded=True)
            self.assertIn('value="true"', xml.read_text())
            self.assertTrue(json.loads(js.read_text())["seeded"])


class GateEndToEnd(unittest.TestCase):
    """Integration boundary: the real gate against the real in-process SUT, not a mocked call."""

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = run_mod.main(argv)
        return rc, out.getvalue() + err.getvalue()

    def test_seeded_gate_is_red_announced_and_stamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            rc, text = self._run(["--sut", MOCK_SHOP, "--seed-bug", "--report", str(path)])
            payload = json.loads(path.read_text())
        self.assertEqual(rc, 1, "a seeded run still fails the gate")
        self.assertIn("SEEDED RUN", text)
        self.assertIn("MANUFACTURED", text)
        self.assertTrue(payload["seeded"], "the artifact must declare the seeding")
        self.assertEqual(payload["failed"], 1)

    def test_healthy_gate_is_green_and_stamped_unseeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            rc, text = self._run(["--sut", MOCK_SHOP, "--report", str(path)])
            payload = json.loads(path.read_text())
        self.assertEqual(rc, 0)
        self.assertNotIn("SEEDED RUN", text)
        self.assertFalse(payload["seeded"])

    def test_seed_bug_against_a_remote_sut_says_it_had_no_effect(self):
        """The honest half: the flag is dropped on a remote runtime, so the gate reports that rather
        than stamping a seeding that never happened. (The run then trips the false-green guard on an
        unreachable SUT, which is the expected exit 2 — what matters here is the warning.)"""
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["QAF_BASE_URL"] = "http://127.0.0.1:9"
            try:
                rc, text = self._run(["--sut", str(ROOT / "sut" / "widget-api"), "--seed-bug",
                                      "--report", str(Path(tmp) / "r.json")])
            finally:
                os.environ.pop("QAF_BASE_URL", None)
        self.assertIn("had NO EFFECT", text)
        self.assertNotIn("SEEDED RUN", text)
        self.assertEqual(rc, 2, "an unreachable SUT trips the false-green guard")


if __name__ == "__main__":
    unittest.main()
