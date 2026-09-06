"""Panel-record lint — every touched validation report states whether the review panel ran.

The review panel (``docs/multiagent/review-panel.md``) under-fires when its trigger is discretionary
prose: every deterministic gate in this repo fires every time, and every remember-to instruction does
not. This lint wires the panel to an artifact every code change already produces — the validation
report (``validation-reports/``, ``policies/methodology.md`` Phase 6) — by requiring a ``Panel``
section that records either ``ran:`` (with a digest / verdict reference) or ``waived:`` (with the
reason).

It gates PRESENCE, not content. The lenses stay advisory and a waiver is legitimate (a docs-only or
tooling-only change; no non-green gate result this cycle); the human reads the waiver on the PR. Scope
is **changed files only** (pre-commit ``pass_filenames``; ``make panel-record`` diffs against ``HEAD``;
CI diffs against the base ref), so historical reports are never retro-gated. ``TEMPLATE.md`` is out of
scope by name: it shows the shape and must not satisfy the lint on its own.

Expected shape anywhere in the report::

    ### Panel
    - ran: R-DIAGNOSIS tier 1 (TEST_BUG, no flags); JUDGE digest in the PR description   # or
    - waived: docs-only change, no failing case this cycle

Exit codes: ``0`` pass (including "no lintable path given"), ``1`` a touched report lacks the record.
"""
from __future__ import annotations

import re
import sys

HEADER_RE = re.compile(r"(?mi)^#{2,4}\s+Panel\b")
ENTRY_RE = re.compile(r"(?mi)^\s*[-*]\s*(ran|waived)\s*:\s*\S+")

HELP = (
    "add a `### Panel` section with `- ran: <digest / verdict ref>` or `- waived: <reason>` — "
    "the review-panel invocation record (docs/multiagent/review-panel.md § Invocation tiers). "
    "The panel is advisory: this gates the RECORD, never the verdict"
)


def check_text(text: str) -> str | None:
    """Return the failure reason for a report body, or ``None`` if it passes."""
    if not HEADER_RE.search(text):
        return f"no `Panel` section: {HELP}"
    if not ENTRY_RE.search(text):
        return f"`Panel` section has no `ran:`/`waived:` entry: {HELP}"
    return None


def is_lintable_path(path: str) -> bool:
    """Validation reports only; the template is the blank the others are copied from."""
    p = path.replace("\\", "/")
    if not (p.startswith("validation-reports/") and p.endswith(".md")):
        return False
    return p.rsplit("/", 1)[-1] != "TEMPLATE.md"


def main(argv: list[str] | None = None) -> int:
    paths = argv if argv is not None else sys.argv[1:]
    failures: list[str] = []
    for path in paths:
        if not is_lintable_path(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except FileNotFoundError:
            continue  # deleted in this change — nothing left to record
        reason = check_text(text)
        if reason:
            failures.append(f"  [PANEL-SECTION-MISSING] {path} — {reason}")
    if failures:
        print("\n".join(failures))
        print(
            "\n  panel-record lint: every touched validation report must record the review-panel "
            "outcome (ran / waived). The panel is advisory; this gates the RECORD, not the verdict."
        )
        return 1
    print("  panel-record lint: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
