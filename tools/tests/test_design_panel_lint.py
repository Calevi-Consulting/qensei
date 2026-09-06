"""Zero-dependency unittest polarity pins for engine/design_panel_lint.py (the Phase-2b design-panel record).

Each pin names the failure it closes — most importantly the traceability half: a `ran: N findings`
record must carry N labelled dispositions, so a finding cannot vanish between the lens and the plan.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from engine.design_panel_lint import check_text, is_lintable_path, main

RAN = (
    "## Design panel\n"
    "- ran: R-DESIGN 3 findings; R-MECHANISM (needs_mechanism)\n"
    "- F1 APPLIED: persona was wrong -> existing_data, durable find-or-created by name\n"
    "- F2 REJECTED: cross-pack reuse — the producer pack is deferred, tracked in the spec\n"
    "- F3 FLAGGED: durable shared under -n auto; accepted, both cases are read-only on it\n"
)
RAN_NO_COUNT = "## Design panel\n- ran: R-DESIGN reviewed the plan, nothing to report\n"
WAIVED = "## Design panel\n- waived: docs-only revision of an already-implemented pack\n"


class CheckText(unittest.TestCase):
    def test_ran_entry_with_matching_dispositions_passes(self):
        self.assertIsNone(check_text(RAN))

    def test_ran_without_a_declared_count_passes(self):
        """"The panel ran and found nothing" is a legitimate record with nothing to reconcile."""
        self.assertIsNone(check_text(RAN_NO_COUNT))

    def test_waived_entry_passes(self):
        """A waiver is legitimate — the lint gates the record, not the verdict."""
        self.assertIsNone(check_text(WAIVED))

    def test_missing_section_fails(self):
        self.assertIn("no `Design panel` section", check_text("## Plan\n\nsome prose\n"))

    def test_section_without_entry_fails(self):
        self.assertIn("no `ran:`/`waived:` entry", check_text("## Design panel\n\nwe thought about it\n"))

    def test_entry_needs_content_after_the_colon(self):
        self.assertIsNotNone(check_text("## Design panel\n- waived:\n"))

    def test_header_level_and_case_are_flexible(self):
        self.assertIsNone(check_text("#### design PANEL\n* ran: x\n"))

    # --- traceability: findings must come BACK into the design ---------------------------------

    def test_declared_count_without_dispositions_fails(self):
        """The defect the count check closes: `ran: N findings` passing with no trace of any decision."""
        reason = check_text("## Design panel\n- ran: R-DESIGN 3 findings — all handled\n")
        self.assertIsNotNone(reason)
        self.assertIn("3 finding(s)", reason)
        self.assertIn("0 disposition", reason)

    def test_partial_dispositions_fail(self):
        text = RAN.replace("- F3 FLAGGED: durable shared under -n auto; accepted, both cases are read-only on it\n", "")
        reason = check_text(text)
        self.assertIsNotNone(reason)
        self.assertIn("2 disposition", reason)

    def test_rejected_passes_exactly_like_applied(self):
        """Requiring findings to be APPLIED would turn an advisory lens into a gate."""
        self.assertIsNone(check_text(RAN.replace("APPLIED", "REJECTED").replace("FLAGGED", "REJECTED")))

    def test_a_disposition_needs_a_reason(self):
        self.assertIsNotNone(check_text("## Design panel\n- ran: 1 finding\n- F1 APPLIED:\n"))

    def test_an_unknown_disposition_word_is_not_counted(self):
        """The set is closed on purpose, so the record stays greppable across packs."""
        self.assertIsNotNone(check_text("## Design panel\n- ran: 1 finding\n- F1 HANDLED: did something\n"))

    def test_duplicate_labels_cannot_pad_the_count(self):
        """F1 twice must not satisfy a 2-finding record — a finding would be silently dropped."""
        reason = check_text("## Design panel\n- ran: 2 findings\n- F1 APPLIED: a\n- F1 REJECTED: b\n")
        self.assertIsNotNone(reason)
        self.assertIn("expected F1..F2", reason)

    def test_the_failure_message_names_who_adjudicates(self):
        """The lint demands dispositions; it must also say whose decision they are — the GENERATOR
        proposes, the HUMAN ratifies, and there is no JUDGE at Phase 2b. Ownership stated only in
        prose drifts; a lint message is the one place a future agent is guaranteed to read."""
        reason = check_text("## Design panel\n- ran: R-DESIGN 2 findings\n- F1 APPLIED: a\n")
        self.assertIsNotNone(reason)
        self.assertIn("proposal", reason.lower())
        self.assertIn("human", reason.lower())

    def test_the_help_text_denies_agent_adjudication(self):
        reason = check_text("no section here at all")
        self.assertIn("no judge", reason.lower())
        self.assertIn("human", reason.lower())


class VacuousPass(unittest.TestCase):
    """Same family as the panel-record lint's: a copied template or an example in a comment must
    never satisfy the record on its own, and only the section's own lines count."""

    def test_placeholder_values_are_not_entries(self):
        self.assertIsNotNone(check_text("## Design panel\n- ran: <N> findings\n- F1 APPLIED: <reason>\n"))
        self.assertIsNotNone(check_text("## Design panel\n- waived: <reason>\n"))

    def test_example_inside_an_html_comment_does_not_count(self):
        self.assertIsNotNone(check_text("## Design panel\n<!--\n- ran: 1 finding\n- F1 APPLIED: x\n-->\n"))

    def test_entries_outside_the_section_do_not_count(self):
        self.assertIsNotNone(check_text("## Notes\n- ran: 1 finding\n- F1 APPLIED: x\n\n## Design panel\nprose\n"))

    def test_dispositions_outside_the_section_are_not_counted(self):
        text = "## Design panel\n- ran: 2 findings\n\n## Rollout\n- F1 APPLIED: a\n- F2 REJECTED: b\n"
        reason = check_text(text)
        self.assertIsNotNone(reason)
        self.assertIn("0 disposition", reason)


class Scope(unittest.TestCase):
    def test_sut_plan_is_lintable(self):
        self.assertTrue(is_lintable_path("sut/mock-shop/plans/2026-09-06-shop-456-bulk-discount.md"))

    def test_spec_is_not_this_lints_business(self):
        self.assertFalse(is_lintable_path("sut/mock-shop/specs/SHOP-456-bulk-discount.md"))

    def test_top_level_specs_and_pack_readmes_are_out_of_scope(self):
        self.assertFalse(is_lintable_path("specs/005-design-panel-and-invocation-tiers.md"))
        self.assertFalse(is_lintable_path("sut/mock-shop/packs/SHOP-456-discount/README.md"))


class Main(unittest.TestCase):
    def _run(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(argv)
        return rc, out.getvalue()

    def test_unrelated_and_missing_paths_never_fail(self):
        rc, _ = self._run(["docs/notes.md", "sut/gone/plans/gone.md"])
        self.assertEqual(rc, 0)

    def test_fails_on_a_plan_without_the_record(self):
        with tempfile.TemporaryDirectory() as tmp, _chdir(tmp):
            d = Path("sut/acme/plans")
            d.mkdir(parents=True)
            (d / "2026-09-06-thing.md").write_text("## Plan\n\nno record\n", encoding="utf-8")
            rc, out = self._run(["sut/acme/plans/2026-09-06-thing.md"])
        self.assertEqual(rc, 1)
        self.assertIn("[DESIGN-PANEL-RECORD-MISSING] sut/acme/plans/2026-09-06-thing.md", out)

    def test_passes_on_a_plan_with_the_record(self):
        with tempfile.TemporaryDirectory() as tmp, _chdir(tmp):
            d = Path("sut/acme/plans")
            d.mkdir(parents=True)
            (d / "2026-09-06-thing.md").write_text("## Plan\n\n" + RAN, encoding="utf-8")
            rc, _ = self._run(["sut/acme/plans/2026-09-06-thing.md"])
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

class RealPlans(unittest.TestCase):
    """Every plan actually committed under sut/<name>/plans/ carries a record the lint accepts.

    Integration pin for spec 005's demonstrator: the first real R-DESIGN run in this repo landed its
    findings + dispositions in `sut/mock-shop/plans/…`, and that record is what the lint gates. If the
    record format and the lint ever drift apart, this is where it shows — on a real file, not a fixture.
    """

    def test_every_committed_plan_passes(self):
        root = Path(__file__).resolve().parents[2]
        plans = sorted(root.glob("sut/*/plans/*.md"))
        self.assertTrue(plans, "expected at least one plan under sut/*/plans/ (the spec-005 demonstrator)")
        for plan in plans:
            rel = plan.relative_to(root).as_posix()
            self.assertTrue(is_lintable_path(rel), rel)
            self.assertIsNone(check_text(plan.read_text(encoding="utf-8")), rel)
