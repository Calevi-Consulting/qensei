"""Zero-dependency unittest polarity pins for engine/panel_section_lint.py (the Phase-4 panel record).

Each pin names the failure it closes. ``main`` is exercised through its real entry point against a
throwaway ``validation-reports/`` tree so the path scoping and exit codes are covered end-to-end.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from engine.panel_section_lint import check_text, is_lintable_path, main

RAN = "# Report\n\n### Panel\n- ran: R-DIAGNOSIS tier 1 (TEST_BUG, no flags)\n"
WAIVED = "# Report\n\n## Panel\n- waived: docs-only change, no failing case this cycle\n"


class CheckText(unittest.TestCase):
    def test_ran_entry_passes(self):
        self.assertIsNone(check_text(RAN))

    def test_waived_entry_passes(self):
        """A waiver is legitimate — the lint gates the record, not the verdict."""
        self.assertIsNone(check_text(WAIVED))

    def test_missing_section_fails(self):
        self.assertIn("no `Panel` section", check_text("# Report\nno panel here\n"))

    def test_section_without_entry_fails(self):
        self.assertIn("no `ran:`/`waived:`", check_text("# R\n### Panel\nsome prose, no entry\n"))

    def test_empty_ran_value_fails(self):
        """`- ran:` with nothing after it records nothing."""
        self.assertIsNotNone(check_text("# R\n### Panel\n- ran:\n"))

    def test_header_level_and_case_are_flexible(self):
        self.assertIsNone(check_text("#### PANEL\n* waived: x\n"))

    def test_the_failure_message_says_it_gates_the_record_not_the_verdict(self):
        """The message is the one place a future author is guaranteed to read the contract."""
        reason = check_text("# R\n")
        self.assertIn("advisory", reason.lower())
        self.assertIn("record", reason.lower())


class VacuousPass(unittest.TestCase):
    """The hole the pre-merge re-verification of spec 005 found: a report copied verbatim from
    TEMPLATE.md satisfied the first version of the lint."""

    def test_the_real_template_does_not_satisfy_the_lint(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "validation-reports" / "TEMPLATE.md").read_text(encoding="utf-8")
        self.assertIsNotNone(check_text(template), "TEMPLATE.md must not pass the lint on its own")

    def test_placeholder_value_is_not_an_entry(self):
        self.assertIsNotNone(check_text("# R\n### Panel\n- ran: <digest ref>\n"))
        self.assertIsNotNone(check_text("# R\n### Panel\n- waived: <reason>\n"))

    def test_entry_inside_an_html_comment_does_not_count(self):
        self.assertIsNotNone(check_text("# R\n### Panel\n<!-- - ran: example -->\n"))

    def test_entry_outside_the_section_does_not_count(self):
        self.assertIsNotNone(check_text("# R\n## What changed\n- ran: the gate twice\n\n### Panel\nprose\n"))

    def test_example_inside_a_fenced_block_does_not_count(self):
        self.assertIsNotNone(check_text("# R\n### Panel\n```\n- ran: example\n```\n"))

    def test_a_hash_line_inside_a_fence_does_not_end_the_section(self):
        self.assertIsNone(check_text("# R\n### Panel\n```sh\n# a comment\n```\n- waived: docs only\n"))

    def test_entry_after_the_next_header_does_not_count(self):
        self.assertIsNotNone(check_text("# R\n### Panel\nprose\n## Result\n- ran: x\n"))


class Scope(unittest.TestCase):
    def test_validation_reports_only(self):
        self.assertTrue(is_lintable_path("validation-reports/2026-09-06-x.md"))
        self.assertFalse(is_lintable_path("docs/overview.md"))
        self.assertFalse(is_lintable_path("validation-reports/notes.txt"))

    def test_template_is_out_of_scope(self):
        """The template shows the shape; it must not satisfy (or fail) the lint on its own."""
        self.assertFalse(is_lintable_path("validation-reports/TEMPLATE.md"))


class Main(unittest.TestCase):
    def _run(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(argv)
        return rc, out.getvalue()

    def test_out_of_scope_and_missing_files_never_fail(self):
        rc, _ = self._run(["docs/whatever.md", "validation-reports/deleted-in-this-change.md"])
        self.assertEqual(rc, 0)

    def test_no_paths_is_clean(self):
        """Nothing touched -> nothing to record (the make target passes an empty list via xargs -r)."""
        rc, _ = self._run([])
        self.assertEqual(rc, 0)

    def test_fails_on_a_report_without_the_record(self):
        with tempfile.TemporaryDirectory() as tmp, _chdir(tmp):
            d = Path("validation-reports")
            d.mkdir()
            (d / "r.md").write_text("# Report\n", encoding="utf-8")
            rc, out = self._run(["validation-reports/r.md"])
        self.assertEqual(rc, 1)
        self.assertIn("[PANEL-SECTION-MISSING] validation-reports/r.md", out)

    def test_passes_on_a_report_with_the_record(self):
        with tempfile.TemporaryDirectory() as tmp, _chdir(tmp):
            d = Path("validation-reports")
            d.mkdir()
            (d / "r.md").write_text(RAN, encoding="utf-8")
            rc, _ = self._run(["validation-reports/r.md"])
        self.assertEqual(rc, 0)


@contextlib.contextmanager
def _chdir(path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


if __name__ == "__main__":
    unittest.main()
