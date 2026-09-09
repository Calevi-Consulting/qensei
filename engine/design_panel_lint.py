"""Design-panel record lint — a touched pack plan states whether R-DESIGN ran, and what was decided.

Sibling of ``panel_section_lint.py``, which records the **Phase-4** review panel in a validation
report. This one records the **Phase-2b** design panel (``agents/r-design.md``,
``docs/multiagent/r-design.md``) in the plan under ``sut/<name>/plans/``. Same principle, and the
principle is the whole reason it exists: a lens whose trigger is prose decays into "we thought about
it"; a record someone has to write does not.

Expected shape anywhere in ``sut/<name>/plans/<file>.md``::

    ## Design panel
    - ran: R-DESIGN 3 findings; R-MECHANISM (needs_mechanism)
    - F1 APPLIED: false-SKIP pre-flight -> `requires` now checks data presence, not the assertion
    - F2 REJECTED: cross-pack reuse — the producer pack is deferred; tracked in <spec>
    - F3 FLAGGED: durable shared with SHOP-DUR under -n auto — accepted, cases are read-only on it

    ## Design panel
    - waived: docs-only revision of an already-implemented pack

**Traceability, not just presence.** When ``ran:`` declares *N* findings the record must carry *N*
disposition lines, labelled ``F1..FN`` each exactly once, each from a CLOSED set with a reason. The
point of Phase 2b is that findings come BACK into the design before implementation; a bare
``ran: yes`` proves the panel was convened and nothing else.

**The declared count is R-DESIGN's.** It is read from ``R-DESIGN <N> findings`` when that phrase is
present, else from the first ``<N> findings`` that is not part of a date or a hyphenated token. A
Tier-2 lens (R-MECHANISM / R-EVIDENCE) verifies or refutes what R-DESIGN flagged; its output is folded
into the ``F<n>`` line it bears on (the demonstrator does this with R-MECHANISM under F3), or named in
the ``ran:`` prose — it does not add labels of its own. A ``ran:`` entry may wrap onto indented
continuation lines; the count is read from the whole entry.

**Whose decision the dispositions are.** The GENERATOR's PROPOSAL, ratified by the HUMAN at the
spec-approval gate that already exists. There is deliberately **no JUDGE at Phase 2b** (a human is one
step away; an adjudicator in front of an adjudicator would make an advisory lens the de-facto design
gate). R-DESIGN itself never writes a disposition. The failure message says so, because an agent
reading only the message would otherwise reasonably conclude it is adjudicating.

It gates **the record, not the verdict**: ``REJECTED`` passes exactly like ``APPLIED`` — requiring
findings to be applied would turn an advisory lens into a gate. A waiver passes with a reason.

Known limit, stated rather than papered over: a count-match is gameable (``ran: 1 finding`` plus one
line passes). It raises the floor; no deterministic lint can prove the record is honest. The
countervailing risk — a heavier format pushing authors toward ``waived:`` — is why the format is one
line per finding and no required prose length.

Scope is **changed files only** — pre-commit passes the staged paths; ``--changed [--base REF]`` (used
by ``make design-panel`` and CI) computes plans changed vs ``HEAD``/``REF`` plus untracked ones.
Existing plans are never retro-gated. Shared rules (``engine/record_lint.py``): entries and
dispositions count only **inside** the ``Design panel`` section (a sub-header does not end it), fenced
code and HTML comments are stripped first, an unfilled ``<placeholder>`` is not an entry, and a bold
label (``- **F1 APPLIED**: …``) or an annotation (``- waived (docs-only): …``) is accepted — so a
copied template or a pasted example never passes on its own.

Exit codes: ``0`` pass (including "nothing to check"), ``1`` a touched plan lacks the record or cannot
be read, ``2`` ``--changed`` could not determine the changed files (never a silent pass).
"""
from __future__ import annotations

import argparse
import re
import sys

from engine.record_lint import lint_paths, resolve_paths, section_body

PATHSPECS = ["sut/*/plans/*.md"]
HEADER_RE = re.compile(r"(?mi)^(?P<h>#{2,4})\s+Design panel\b")
# `\**` tolerates a bold label; `(…)` an annotation such as `- waived (Phase 4): …`;
# `(?!<)` rejects an unfilled `<placeholder>`.
ENTRY_RE = re.compile(r"(?mi)^\s*[-*]\s*\**(ran|waived)\**\s*(?:\([^)\n]{0,60}\)\s*)?:\**\s*(?!<)\S+")
# The whole `ran:` list item, including indented continuation lines that are not themselves items.
RAN_RE = re.compile(
    r"(?mi)^\s*[-*]\s*\**ran\**\s*(?:\([^)\n]{0,60}\)\s*)?:\**\s*(?!<)(?P<body>.+(?:\n[ \t]+(?![-*\s])\S.*)*)"
)
# R-DESIGN's count. Prefer the phrase that names the lens; else the first `<N> findings` whose digits
# are not the tail of a date / hyphenated token (`2026-09-06 findings` must not read as 6), and
# `finding` is the whole word (`1 finding-free pass` declares nothing).
COUNT_DESIGN_RE = re.compile(r"(?i)R-DESIGN[^\d\n]{0,24}?(\d{1,3})\s+findings?\b(?!-)")
COUNT_ANY_RE = re.compile(r"(?i)(?<![\w.\-])(\d{1,3})\s+findings?\b(?!-)")
# `- F3 REJECTED: reason`. The disposition set is CLOSED so the record stays greppable across packs;
# the reason is required because a bare verdict tells the next reader nothing about why.
DISPOSITIONS = ("APPLIED", "REJECTED", "FLAGGED", "DEFERRED")
FINDING_RE = re.compile(
    r"(?mi)^\s*[-*]\s*\**F(?P<n>\d+)\s+(?P<disp>" + "|".join(DISPOSITIONS) + r")\**\s*:\**\s*(?!<)(?P<why>\S.*)$"
)
PLAN_PATH_RE = re.compile(r"^sut/[^/]+/plans/[^/]+\.md$")

HELP = (
    "add a `## Design panel` section with `- ran: R-DESIGN <N> findings` plus one `- F<n> "
    "APPLIED|REJECTED|FLAGGED|DEFERRED: <reason>` line per finding, or `- waived: <reason>` — "
    "the Phase-2b design-review record (docs/multiagent/r-design.md). The dispositions are the "
    "GENERATOR's PROPOSAL; the HUMAN ratifies them at the spec-approval gate. There is no JUDGE at "
    "Phase 2b and no agent decides which findings are taken"
)


def declared_count(ran_body: str) -> int | None:
    """R-DESIGN's finding count from a ``ran:`` entry, or ``None`` when none is declared."""
    m = COUNT_DESIGN_RE.search(ran_body) or COUNT_ANY_RE.search(ran_body)
    return int(m.group(1)) if m else None


def _reconcile(declared: int, body: str) -> str | None:
    """The traceability check: *declared* dispositions, labelled F1..FN each exactly once."""
    dispositions = FINDING_RE.findall(body)
    if len(dispositions) != declared:
        return (
            f"`ran:` declares {declared} finding(s) but the record carries {len(dispositions)} "
            f"disposition line(s). Phase 2b exists so findings come BACK into the design — write one "
            f"`- F<n> {'|'.join(DISPOSITIONS)}: <reason>` line per finding. "
            f"REJECTED passes like APPLIED: this gates the record, not the verdict. What you write "
            f"is a PROPOSAL the human ratifies at the spec-approval gate — you are not adjudicating."
        )
    seen = sorted(int(n) for n, _disp, _why in dispositions)
    if seen != list(range(1, declared + 1)):
        return (
            f"disposition labels are F{seen} — expected F1..F{declared}, each exactly once, so a "
            "finding cannot be silently dropped or double-counted."
        )
    return None


def check_text(text: str) -> str | None:
    """Return the failure reason for a plan body, or ``None`` if it passes."""
    body = section_body(text, HEADER_RE)
    if body is None:
        return f"no `Design panel` section: {HELP}"
    if not ENTRY_RE.search(body):
        return f"`Design panel` section has no `ran:`/`waived:` entry: {HELP}"
    ran = RAN_RE.search(body)
    if ran is None:
        return None  # `waived:` only — a documented waiver needs no dispositions.
    declared = declared_count(ran.group("body"))
    if declared is None:
        return None  # no declared count -> nothing to reconcile ("the panel ran, nothing to report").
    return _reconcile(declared, body)


def is_lintable_path(path: str) -> bool:
    """Only plans under a SUT plugin (``sut/<name>/plans/<file>.md``)."""
    return bool(PLAN_PATH_RE.match(path.replace("\\", "/")))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Qensei design-panel record lint (sut/<name>/plans)")
    ap.add_argument("paths", nargs="*", help="plan files to check (pre-commit passes the staged ones)")
    ap.add_argument("--changed", action="store_true",
                    help="check plans changed vs --base (default HEAD) plus untracked ones")
    ap.add_argument("--base", default=None, help="revision (or A...B range) for --changed; default HEAD")
    args = ap.parse_args(argv)
    paths, rc = resolve_paths(args, PATHSPECS, "design-panel lint")
    if paths is None:
        return rc
    return lint_paths(
        paths, is_lintable=is_lintable_path, check_text=check_text, tag="DESIGN-PANEL-RECORD-MISSING",
        name="design-panel lint",
        epilogue="a touched pack plan must record whether the Phase-2b design panel ran (R-DESIGN) or was "
                 "waived, AND what was decided about each finding. The panel is advisory; this gates the "
                 "RECORD, not the verdict — REJECTED passes like APPLIED, and a documented waiver passes.",
    )


if __name__ == "__main__":
    sys.exit(main())
