"""Multi-site seam tests — the framework working against TWO sites, isolated per site.

These exercise the real integration boundary the unit tests in test_engine.py do not: they
BOOT the restful-booker mock in-process and run its packs / diagnostics against the live
runtime, and they assert one site's gate never discovers another site's cases. AI-generated
plumbing can pass every unit check yet wire the wrong packs dir to a SUT — only a booted,
cross-site run catches that.

Run: ``python -m unittest discover -s tools/tests`` (or ``make test-engine``).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine import diagnostics, runner  # noqa: E402
from engine.config import Settings  # noqa: E402
from engine.credentials import CredentialError  # noqa: E402
from engine.sut import SUTConnector  # noqa: E402

MOCK_SHOP = str(ROOT / "sut" / "mock-shop")
BOOKER = str(ROOT / "sut" / "restful-booker")


def _quiet(fn, *a, **k):
    """Run a noisy gate/diagnose call with stdout suppressed; return its result."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


class TestPacksDirResolution(unittest.TestCase):
    """The per-SUT `tests` block resolves each site's own packs/specs/tickets dirs."""

    def _sut(self, manifest: dict) -> SUTConnector:
        d = tempfile.mkdtemp()
        (Path(d) / "manifest.json").write_text(json.dumps(manifest))
        return SUTConnector(d, settings=Settings())

    def test_custom_tests_block(self):
        sut = self._sut({"name": "x", "source": {"path": "src"},
                         "runtime": {"mode": "in_process", "app": "app.py"},
                         "tests": {"packs": "regressions", "specs": "intents", "tickets": "issues"}})
        self.assertEqual(sut.packs_dir.name, "regressions")
        self.assertEqual(sut.specs_dir.name, "intents")
        self.assertEqual(sut.tickets_dir.name, "issues")

    def test_default_when_no_tests_block(self):
        sut = self._sut({"name": "y", "source": {"path": "src"},
                         "runtime": {"mode": "in_process", "app": "app.py"}})
        self.assertEqual(sut.packs_dir.name, "packs")
        self.assertEqual(sut.specs_dir.name, "specs")

    def test_real_plugins_point_at_their_own_packs(self):
        self.assertEqual(SUTConnector(MOCK_SHOP).packs_dir, (ROOT / "sut" / "mock-shop" / "packs").resolve())
        self.assertEqual(SUTConnector(BOOKER).packs_dir, (ROOT / "sut" / "restful-booker" / "packs").resolve())


class TestRuntimeModeAndCreds(unittest.TestCase):
    """An env may override runtime mode; QAF_CREDS_MODE overrides the manifest creds.mode."""

    def test_env_overrides_runtime_mode(self):
        self.assertEqual(SUTConnector(BOOKER, settings=Settings(env="live")).runtime_mode(), "remote")
        self.assertEqual(SUTConnector(BOOKER, settings=Settings(env="local")).runtime_mode(), "in_process")
        self.assertEqual(SUTConnector(BOOKER, settings=Settings()).runtime_mode(), "in_process")

    def test_creds_mode_override_plumbs_through_settings(self):
        self.assertEqual(Settings.load(overrides={"CREDS_MODE": "provider"}).creds_mode, "provider")
        self.assertIsNone(Settings.load().creds_mode)


class TestSiteIsolation(unittest.TestCase):
    """Each site's gate discovers only its OWN cases — no cross-contamination."""

    def test_gate_discovers_only_its_site(self):
        shop_ids = {c.id for c in runner.discover_cases(str(SUTConnector(MOCK_SHOP).packs_dir))}
        booker_ids = {c.id for c in runner.discover_cases(str(SUTConnector(BOOKER).packs_dir))}
        self.assertEqual(shop_ids, {"SHOP-123", "SHOP-456", "SHOP-DUR"})
        self.assertTrue(booker_ids and all(i.startswith("BOOK") for i in booker_ids))
        self.assertEqual(shop_ids & booker_ids, set())


class TestBookerBooted(unittest.TestCase):
    """Boot the restful-booker mock and exercise its real runtime end-to-end."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["QAF_BOOKER_STATE"] = str(Path(self._tmp.name) / "rooms.json")

    def tearDown(self):
        os.environ.pop("QAF_BOOKER_STATE", None)
        self._tmp.cleanup()

    def test_booker_gate_is_green(self):
        sut = SUTConnector(BOOKER)
        sut.start()
        try:
            results = _quiet(runner.run_packs, sut, str(sut.packs_dir))
        finally:
            sut.stop()
        self.assertTrue(results, "the booker gate discovered no cases")
        statuses = {r[0].id: r[3] for r in results}
        self.assertTrue(all(s == "PASS" for s in statuses.values()), statuses)

    def test_seed_bug_is_real_bug(self):
        sut = SUTConnector(BOOKER)
        sut.start(buggy=True)
        try:
            case = runner.load_pack_case(str(ROOT / "sut/restful-booker/packs/BOOK-2-longstay-discount"))
            d = _quiet(diagnostics.diagnose, case, sut)
        finally:
            sut.stop()
        self.assertEqual(d["verdict"], "REAL_BUG")

    def test_bad_test_is_test_bug(self):
        sut = SUTConnector(BOOKER)
        sut.start(buggy=False)
        try:
            case = runner.load_pack_case(str(ROOT / "sut/restful-booker/examples/diagnostics/BOOK-789-bad-test"))
            d = _quiet(diagnostics.diagnose, case, sut)
        finally:
            sut.stop()
        self.assertEqual(d["verdict"], "TEST_BUG")

    def test_malformed_input_gets_4xx_not_a_crash(self):
        """Bad input must yield a clean HTTP 4xx — never an unhandled crash / dropped socket
        (which the connector would otherwise mis-surface as ENV_OR_TRANSIENT)."""
        sut = SUTConnector(BOOKER)
        sut.start()
        try:
            base = {"firstname": "A", "lastname": "B"}
            # non-integer roomid -> 400
            s, _ = sut.post("/booking/", {**base, "roomid": "abc",
                                          "bookingdates": {"checkin": "2025-01-01", "checkout": "2025-01-03"}})
            self.assertEqual(s, 400)
            # bookingdates sent as a non-object -> 400
            s, _ = sut.post("/booking/", {**base, "roomid": 1, "bookingdates": "not-an-object"})
            self.assertEqual(s, 400)
            # non-date strings -> 400
            s, _ = sut.post("/booking/", {**base, "roomid": 1,
                                          "bookingdates": {"checkin": "nope", "checkout": "nope"}})
            self.assertEqual(s, 400)
            # non-integer roomid on the summary query -> 400
            s, _ = sut.get("/booking/summary?roomid=abc")
            self.assertEqual(s, 400)
            # non-integer roomPrice on room create -> 400
            s, _ = sut.post("/room/", {"roomName": "qaf-bad-price-room", "roomPrice": "lots"})
            self.assertEqual(s, 400)
        finally:
            sut.stop()

    def test_provider_login_returns_cookie(self):
        """The plugin's resolve_creds performs the real cookie-login flow (the live-env seam)."""
        sut = SUTConnector(BOOKER)
        sut.start()
        try:
            plugin = sut.plugin()
            ok = plugin.resolve_creds(Settings(base_url=sut.base_url, username="admin", password="password"))
            self.assertIn("token=", ok["headers"]["Cookie"])
            with self.assertRaises(CredentialError):
                plugin.resolve_creds(Settings(base_url=sut.base_url, username="admin", password="wrong"))
        finally:
            sut.stop()


if __name__ == "__main__":
    unittest.main()
