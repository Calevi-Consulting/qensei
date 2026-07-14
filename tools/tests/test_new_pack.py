"""Zero-dependency unittest coverage for scripts/new_pack.py (the pack scaffolder).

Drives the scaffolder through its real entry point (``new_pack.main``) in a throwaway repo tree
(``new_pack.ROOT`` is redirected to a temp dir), then asserts:

  * REST mode output is byte-for-byte unchanged (a golden guard on the REST templates — spec 004 R4);
  * ``--ui`` emits a ``UICase`` into ``ui-packs/`` with the honest, non-false-green TODO skeleton;
  * both modes perform the atomic claim (refuse to overwrite an existing pack);
  * ``--ui`` is self-documented in the module docstring;
  * a scaffolded UI pack is DISCOVERED by the real ``engine.ui.discover_ui_cases`` path — the same
    discovery the Playwright UI bridge (tests/test_ui.py) uses — i.e. the integration-boundary AC, not
    a mocked file read.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.ui import UICase, discover_ui_cases

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("new_pack", _ROOT / "scripts" / "new_pack.py")
new_pack = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(new_pack)

# Frozen golden of the REST scaffolder output (TICKET=SHOP-9 SLUG=widget-restock, --sut sut/demo).
# Captured from the pre-change scaffolder; any drift in the REST templates must fail loudly.
_GOLDEN_REST_CASE = '''"""SHOP-9-widget-restock — widget restock (new_user, REST)."""
from engine.case import RegressionCase


class WidgetRestock(RegressionCase):
    id = "SHOP-9-widget-restock"
    title = "widget restock"
    spec_ref = "sut/demo/specs/SHOP-9-widget-restock.md"
    persona = "new_user"          # or "existing_data"
    tags = frozenset({"smoke"})  # selection lane(s)
    severity = "medium"            # critical | high | medium | low
    requires = []                  # pre-flight requirement keys (see engine/preflight.py)
    covers = []                    # endpoints + business-rule ids (read by design)

    def run(self, sut, expect):
        status, body = sut.get("/")
        expect.is_not_none(body, "TODO: assert the behavioral contract")

    # def teardown(self, sut):     # new_user: delete what you created (best-effort)
    #     ...
'''

_GOLDEN_REST_README = """# SHOP-9-widget-restock — widget restock  · spec'd

REST regression (`new_user`). TODO: one-paragraph index card — what contract it pins and why.

- Spec: [`sut/demo/specs/SHOP-9-widget-restock.md`](../../specs/SHOP-9-widget-restock.md)
- Covers: TODO
- Tags: `smoke`
- Run: `python3 -m engine.run --sut sut/demo` (auto-discovered; filter a lane with `--select smoke`)
"""


class NewPackScaffolder(unittest.TestCase):
    def _sut_root(self) -> Path:
        """A temp repo root holding one minimal ``sut/demo`` plugin (just a manifest)."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "sut" / "demo").mkdir(parents=True)
        (tmp / "sut" / "demo" / "manifest.json").write_text(json.dumps({"name": "demo"}))
        return tmp

    def _run(self, tmp: Path, argv):
        """Run new_pack.main against the temp root (ROOT redirected), capturing stdout."""
        old_root = new_pack.ROOT
        new_pack.ROOT = tmp
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = new_pack.main(argv)
        finally:
            new_pack.ROOT = old_root
        return rc, buf.getvalue()

    def test_rest_output_is_byte_identical(self):
        tmp = self._sut_root()
        rc, _ = self._run(tmp, ["--sut", "sut/demo", "SHOP-9", "widget-restock"])
        self.assertEqual(rc, 0)
        pack = tmp / "sut" / "demo" / "packs" / "SHOP-9-widget-restock"
        self.assertEqual((pack / "case.py").read_text(), _GOLDEN_REST_CASE)
        self.assertEqual((pack / "README.md").read_text(), _GOLDEN_REST_README)
        # REST lands in packs/, never ui-packs/.
        self.assertFalse((tmp / "sut" / "demo" / "ui-packs").exists())

    def test_ui_mode_scaffolds_uicase_into_ui_packs(self):
        tmp = self._sut_root()
        rc, out = self._run(tmp, ["--sut", "sut/demo", "--ui", "BOOK-UI-9", "cancel-flow"])
        self.assertEqual(rc, 0)
        pack = tmp / "sut" / "demo" / "ui-packs" / "BOOK-UI-9-cancel-flow"
        self.assertTrue(pack.is_dir(), "UI pack must land in ui-packs/")
        self.assertFalse((tmp / "sut" / "demo" / "packs").exists(), "UI pack must NOT land in packs/")
        case = (pack / "case.py").read_text()
        self.assertIn("from engine.ui import UICase", case)
        self.assertIn("class CancelFlow(UICase):", case)
        self.assertIn("def run(self, page, base_url, expect):", case)
        self.assertIn('tags = frozenset({"ui"})', case)
        self.assertIn("- Tags: `ui`", (pack / "README.md").read_text())
        # the spec stub is created alongside, kind-agnostic.
        self.assertTrue((tmp / "sut" / "demo" / "specs" / "BOOK-UI-9-cancel-flow.md").exists())

    def test_ui_skeleton_is_honest_not_false_green(self):
        """The scaffolded UI run() must be an explicit failing TODO, not a passing assertion (spec 004 R6)."""
        tmp = self._sut_root()
        self._run(tmp, ["--sut", "sut/demo", "--ui", "BOOK-UI-9", "cancel-flow"])
        case = (tmp / "sut" / "demo" / "ui-packs" / "BOOK-UI-9-cancel-flow" / "case.py").read_text()
        self.assertIn('expect.that(False,', case, "an un-filled UI skeleton must not merge green")

    def test_atomic_claim_refuses_overwrite(self):
        for argv, sub in (
            (["--sut", "sut/demo", "SHOP-9", "widget-restock"], "packs"),
            (["--sut", "sut/demo", "--ui", "BOOK-UI-9", "cancel-flow"], "ui-packs"),
        ):
            with self.subTest(sub=sub):
                tmp = self._sut_root()
                rc1, _ = self._run(tmp, argv)
                self.assertEqual(rc1, 0)
                rc2, out2 = self._run(tmp, argv)
                self.assertEqual(rc2, 1, "second scaffold of the same id must refuse to overwrite")
                self.assertIn("refusing to overwrite", out2)

    def test_ui_flag_is_self_documented(self):
        self.assertIn("--ui", new_pack.__doc__ or "", "the module docstring must document --ui")

    def test_scaffolded_ui_pack_is_discovered_by_the_ui_bridge(self):
        """Integration-boundary AC: the scaffolded UI pack is found by the real discovery path
        (engine.ui.discover_ui_cases — what tests/test_ui.py collects), not a mocked file check."""
        tmp = self._sut_root()
        rc, _ = self._run(tmp, ["--sut", "sut/demo", "--ui", "BOOK-UI-9", "cancel-flow"])
        self.assertEqual(rc, 0)
        cases = discover_ui_cases(str(tmp / "sut" / "demo" / "ui-packs"))
        by_id = {c.id: c for c in cases}
        self.assertIn("BOOK-UI-9-cancel-flow", by_id, "the UI bridge's discovery must find the new pack")
        self.assertTrue(issubclass(by_id["BOOK-UI-9-cancel-flow"], UICase))


if __name__ == "__main__":
    unittest.main()
