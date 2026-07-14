"""Zero-dependency unittest coverage for engine/coverage_lint.py (the coverage-metadata gate).

Each test builds a throwaway ``sut/<name>/...`` tree in a temp dir, chdirs into it, and runs the
gate through its real entry point (``coverage_lint.main``) so the glob, exit codes, and
SUTConnector-backed source resolution are all exercised end-to-end — including the sourceless
degradation path and a brand-new pack with no git baseline.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from engine import coverage_lint

_CASE_TMPL = '''from engine.case import RegressionCase


class C(RegressionCase):
    id = {id!r}
    spec_ref = {spec_ref!r}
    persona = "new_user"
    tags = frozenset({{"smoke"}})
    severity = "high"
    covers = {covers!r}
{claim_line}
    def run(self, sut, expect):
{run_body}
'''


class _Tree:
    """A temp repo root holding one or more ``sut/<name>`` plugins, built pack by pack."""

    def __init__(self, root: Path):
        self.root = root
        self._n = 0

    def sut(self, name: str, *, sourceless: bool = False,
            routes=(("GET", "/x", "x"), ("POST", "/y", "y")), rules=("rule-a",),
            tests=None, broken_source: bool = False) -> str:
        d = self.root / "sut" / name
        (d / "specs").mkdir(parents=True, exist_ok=True)
        if sourceless:
            manifest = {"name": name,
                        "runtime": {"mode": "remote", "base_url": "http://example.invalid"},
                        "creds": {"mode": "none"}}
        else:
            manifest = {"name": name, "source": {"path": "source"},
                        "runtime": {"mode": "in_process", "app": "app.py", "factory": "make_server"},
                        "creds": {"mode": "none"}}
            src = d / "source"
            src.mkdir(parents=True, exist_ok=True)
            (src / "__init__.py").write_text("")
            if broken_source:
                (src / "app.py").write_text("raise RuntimeError('boom at import')\n")
            else:
                rule_lits = ", ".join("{" + f"'id': {r!r}" + "}" for r in rules)
                (src / "app.py").write_text(
                    f"ROUTES = {list(routes)!r}\nBUSINESS_RULES = [{rule_lits}]\n"
                    "def make_server(**k):\n    raise NotImplementedError\n"
                )
        if tests:
            manifest["tests"] = tests
        (d / "manifest.json").write_text(json.dumps(manifest))
        return name

    def pack(self, sut_name: str, pack_id: str, covers_case, covers_readme, *,
             kind: str = "packs", spec_ref: str = "__auto__", contract_claim=None,
             run_body: str = "        expect.that(True, 'ok')",
             covers_style: str = "plain", omit_covers_line: bool = False,
             make_spec: bool = True) -> Path:
        pack_dir = self.root / "sut" / sut_name / kind / pack_id
        pack_dir.mkdir(parents=True, exist_ok=True)
        if spec_ref == "__auto__":
            spec_ref = f"sut/{sut_name}/specs/{pack_id}.md"
        claim_line = f"    contract_claim = {contract_claim!r}\n" if contract_claim is not None else ""
        pack_dir.joinpath("case.py").write_text(_CASE_TMPL.format(
            id=pack_id, spec_ref=spec_ref, covers=list(covers_case),
            claim_line=claim_line, run_body=run_body))

        lines = [f"# {pack_id}", ""]
        if not omit_covers_line:
            toks = ", ".join(f"`{t}`" for t in covers_readme)
            lines.append(f"- **Covers:** {toks}" if covers_style == "bold" else f"- Covers: {toks}")
        pack_dir.joinpath("README.md").write_text("\n".join(lines) + "\n")

        if make_spec and spec_ref.startswith(f"sut/{sut_name}/specs/"):
            (self.root / spec_ref).write_text(f"# {pack_id}\n## Status: COMPLETE\n")
        return pack_dir


class CoverageLintTest(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._env = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("QAF_")}
        self._dir = tempfile.mkdtemp(prefix="covlint_")
        os.chdir(self._dir)
        self.tree = _Tree(Path(self._dir))
        self._sut_n = 0

    def tearDown(self):
        os.chdir(self._cwd)
        os.environ.update(self._env)

    def _name(self) -> str:
        self._sut_n += 1
        return f"fix{self._sut_n}"

    def _run(self, argv=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = coverage_lint.main(argv or [])
        return code, buf.getvalue()

    # --- happy paths ---------------------------------------------------------

    def test_consistent_pass(self):
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x", "POST /y"], ["GET /x", "POST /y"])
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertIn("no coverage-metadata violations", out)

    def test_both_covers_formats_parse(self):
        # bold `- **Covers:**` (widget-api's house style) must parse identically to plain.
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"], covers_style="bold")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_contract_claim_resolves_pass(self):
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"], contract_claim={"rule": "rule-a", "value": 1})
        code, out = self._run()
        self.assertEqual(code, 0, out)

    # --- BLOCKs --------------------------------------------------------------

    def test_covers_inconsistent_block(self):
        # Reconstructs PR #26's BOOK-UI-2: case.py covers a token the README (honestly) dropped.
        s = self.tree.sut(self._name(), routes=(("GET", "/ui", ""), ("GET", "/room/", ""),
                                                ("POST", "/booking/", "")))
        self.tree.pack(s, "BOOK-UI-2",
                       ["GET /ui", "GET /room/", "POST /booking/"],
                       ["GET /ui", "GET /room/"])
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("covers-inconsistent", out)
        self.assertIn("POST /booking/", out)

    def test_cover_unresolved_block(self):
        # Reconstructs SHOP-DUR pre-#28: a cover token that no ROUTE matches (exact-string).
        s = self.tree.sut(self._name(), routes=(("GET", "/accounts/{name}", ""),))
        self.tree.pack(s, "SHOP-DUR", ["GET /accounts/{id}"], ["GET /accounts/{id}"])
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("cover-unresolved", out)

    def test_contract_claim_unresolved_block(self):
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"], contract_claim={"rule": "ghost-rule"})
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("contract_claim-unresolved", out)

    def test_spec_ref_dangling_block(self):
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"],
                       spec_ref=f"sut/{s}/specs/does-not-exist.md", make_spec=False)
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("spec_ref-dangling", out)

    def test_spec_ref_missing_block(self):
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"], spec_ref="", make_spec=False)
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("spec_ref-missing", out)

    def test_readme_covers_missing_block(self):
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], [], omit_covers_line=True)
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("readme-covers-missing", out)

    # --- sourceless degradation (R7 / AC8) -----------------------------------

    def test_sourceless_skips_validity_but_runs_consistency(self):
        # A cover that would be INVALID on a sourced SUT must NOT fail on a sourceless one...
        s = self.tree.sut(self._name(), sourceless=True)
        self.tree.pack(s, "W1", ["POST /widgets", "GET /widgets/{id}"],
                       ["POST /widgets", "GET /widgets/{id}"],
                       contract_claim={"rule": "anything"})
        code, out = self._run()
        self.assertEqual(code, 0, out)
        self.assertIn("UNVERIFIED", out)
        self.assertNotIn("cover-unresolved", out)
        self.assertNotIn("contract_claim-unresolved", out)

    def test_sourceless_still_gates_consistency(self):
        # ...but consistency (source-independent) still gates on a sourceless SUT.
        s = self.tree.sut(self._name(), sourceless=True)
        self.tree.pack(s, "W1", ["POST /widgets", "GET /widgets/{id}"], ["POST /widgets"])
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("covers-inconsistent", out)

    # --- WARN, not BLOCK (R8 / AC10) -----------------------------------------

    def test_duplicate_run_body_warn_not_block(self):
        body = "        x = 1\n        expect.that(x == 1, 'ok')"
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"], run_body=body)
        self.tree.pack(s, "P2", ["POST /y"], ["POST /y"], run_body=body)
        code, out = self._run()
        self.assertEqual(code, 0, out)  # WARN alone still passes
        self.assertIn("duplicate-run-body", out)
        self.assertIn("warn", out)

    # --- structural properties ----------------------------------------------

    def test_new_pack_no_git_baseline_is_evaluated(self):
        # The fixture pack is never committed to git, yet the gate BLOCKs its drift — proving it
        # does not share fidelity_lint's "no baseline -> nothing to check" blind spot (AC9).
        s = self.tree.sut(self._name())
        self.tree.pack(s, "NEW", ["GET /x", "POST /y"], ["GET /x"])  # inconsistent
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("covers-inconsistent", out)

    def test_no_packs_returns_2(self):
        # Empty run must never look like a pass (false-green-guard convention).
        code, out = self._run()
        self.assertEqual(code, 2, out)
        self.assertIn("no packs discovered", out)

    def test_explicit_readme_path_maps_to_its_pack(self):
        s = self.tree.sut(self._name())
        pack = self.tree.pack(s, "P1", ["GET /x", "POST /y"], ["GET /x"])  # inconsistent
        code, out = self._run([str(pack / "README.md")])
        self.assertEqual(code, 1, out)
        self.assertIn("covers-inconsistent", out)

    # --- fixes surfaced by the adversarial review ----------------------------

    def test_prose_covers_bullet_before_metadata_line_passes(self):
        # A narrative "Covers ..." bullet before the real `- Covers: `...`` line must not shadow it.
        s = self.tree.sut(self._name())
        pack = self.tree.pack(s, "P1", ["GET /x"], ["GET /x"])
        pack.joinpath("README.md").write_text(
            "# P1\n\n- Covers the create + read happy paths end to end\n\n- Covers: `GET /x`\n")
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_co_copied_readme_fragility_passes_with_only_dup_warn(self):
        # AC11/AC14: when case.py AND README agree on a wrong-but-resolving covers set, every gated
        # check is green — only the duplicate-run-body detector WARNs. Encodes the admitted evasion
        # (a copy-paste author who also copies the README) as a test, not prose.
        body = "        x = 1\n        expect.that(x == 1, 'ok')"
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"], run_body=body)
        self.tree.pack(s, "P2", ["GET /x"], ["GET /x"], run_body=body)  # copies body AND covers
        code, out = self._run()
        self.assertEqual(code, 0, out)            # the evasion is NOT deterministically caught
        self.assertIn("duplicate-run-body", out)  # only the WARN net fires
        self.assertNotIn("[BLOCK]", out)

    def test_readme_overclaims_covers_block(self):
        # Consistency must gate BOTH directions: a README claiming MORE than case.py also BLOCKs.
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x", "POST /y"])
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("covers-inconsistent", out)
        self.assertIn("only in README", out)
        self.assertIn("POST /y", out)

    def test_contract_claim_malformed_block(self):
        # A non-dict contract_claim (a bare string) must BLOCK, not fail open.
        s = self.tree.sut(self._name())
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"], contract_claim="ghost-rule")
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("contract_claim-malformed", out)

    def test_spec_ref_outside_specs_dir_block(self):
        # spec_ref must resolve UNDER the SUT's specs dir, not merely exist somewhere.
        s = self.tree.sut(self._name())
        pack = self.tree.pack(s, "P1", ["GET /x"], ["GET /x"],
                              spec_ref=f"sut/{s}/packs/P1/README.md", make_spec=False)
        self.assertTrue((pack / "README.md").exists())  # the target exists, but is not a spec
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("spec_ref-misplaced", out)

    def test_source_import_error_block(self):
        # A source-backed SUT whose source will not import is a clean BLOCK, not a crash.
        s = self.tree.sut(self._name(), broken_source=True)
        self.tree.pack(s, "P1", ["GET /x"], ["GET /x"])
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("source-load-error", out)

    def test_custom_packs_dir_is_discovered(self):
        # Discovery honors a manifest that customizes tests.packs, not the literal "packs" (R0).
        s = self.tree.sut(self._name(), tests={"packs": "cases"})
        self.tree.pack(s, "P1", ["GET /x", "POST /y"], ["GET /x"], kind="cases")  # inconsistent
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("covers-inconsistent", out)


if __name__ == "__main__":
    unittest.main()
