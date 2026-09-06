"""Panel-record lint — every touched validation report states whether the review panel ran.

The review panel (``docs/multiagent/review-panel.md``) under-fires when its trigger is discretionary
prose: every deterministic gate in this repo fires every time, and every remember-to instruction does
not. This lint wires the panel to an artifact every code change already produces — the validation
report (``validation-reports/``, ``policies/methodology.md`` Phase 6) — by requiring a ``Panel``
section that records either ``ran:`` (with a digest / verdict reference) or ``waived:`` (with the
reason).

It gates PRESENCE, not content. The lenses stay advisory and a waiver is legitimate (a docs-only or
tooling-only change; no non-green gate result this cycle); the human reads the waiver on the PR. Scope
is **changed files only** — pre-commit passes the staged paths; ``--changed [--base REF]`` (used by
``make panel-record`` and CI) computes files changed vs ``HEAD``/``REF`` plus untracked ones — so
historical reports are never retro-gated. ``TEMPLATE.md`` is out of scope by name.

Rules that close the vacuous-pass hole (``engine/record_lint.py``): the entry must sit **inside** the
``Panel`` section; fenced code and HTML comments are stripped first; an unfilled ``<placeholder>`` is not
an entry. A bold label (``- **ran:** …``) is accepted.

Expected shape anywhere in the report::

    ### Panel
    - ran: R-DIAGNOSIS tier 1 (TEST_BUG, no flags); JUDGE digest in the PR description   # or
    - waived: docs-only change, no failing case this cycle

Exit codes: ``0`` pass (including "nothing to check"), ``1`` a touched report lacks the record or
cannot be read, ``2`` ``--changed`` could not determine the changed files (never a silent pass).
"""
from __future__ import annotations

import argparse
import re
import sys

from engine.record_lint import lint_paths, resolve_paths, section_body

PATHSPECS = ["validation-reports/*.md"]
HEADER_RE = re.compile(r"(?mi)^(?P<h>#{2,4})\s+Panel\b")
# `\**` tolerates a bold label; `(?!<)` rejects an unfilled `<placeholder>`.
ENTRY_RE = re.compile(r"(?mi)^\s*[-*]\s*\**(ran|waived)\**\s*:\**\s*(?!<)\S+")

HELP = (
    "add a `### Panel` section with `- ran: <digest / verdict ref>` or `- waived: <reason>` — "
    "the review-panel invocation record (docs/multiagent/review-panel.md § Invocation tiers). "
    "The panel is advisory: this gates the RECORD, never the verdict"
)


def check_text(text: str) -> str | None:
    """Return the failure reason for a report body, or ``None`` if it passes."""
    body = section_body(text, HEADER_RE)
    if body is None:
        return f"no `Panel` section: {HELP}"
    if not ENTRY_RE.search(body):
        return f"`Panel` section has no `ran:`/`waived:` entry: {HELP}"
    return None


def is_lintable_path(path: str) -> bool:
    """Validation reports only; the template is the blank the others are copied from."""
    p = path.replace("\\", "/")
    if not (p.startswith("validation-reports/") and p.endswith(".md")):
        return False
    return p.rsplit("/", 1)[-1] != "TEMPLATE.md"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Qensei review-panel record lint (validation reports)")
    ap.add_argument("paths", nargs="*", help="report files to check (pre-commit passes the staged ones)")
    ap.add_argument("--changed", action="store_true",
                    help="check reports changed vs --base (default HEAD) plus untracked ones")
    ap.add_argument("--base", default=None, help="revision (or A...B range) for --changed; default HEAD")
    args = ap.parse_args(argv)
    paths, rc = resolve_paths(args, PATHSPECS, "panel-record lint")
    if paths is None:
        return rc
    return lint_paths(
        paths, is_lintable=is_lintable_path, check_text=check_text, tag="PANEL-SECTION-MISSING",
        name="panel-record lint",
        epilogue="every touched validation report must record the review-panel outcome (ran / waived). "
                 "The panel is advisory; this gates the RECORD, not the verdict.",
    )


if __name__ == "__main__":
    sys.exit(main())
