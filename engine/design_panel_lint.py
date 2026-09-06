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

Scope is **changed files only** (pre-commit ``pass_filenames``; ``make design-panel`` diffs against
``HEAD``; CI diffs against the base ref). Existing plans are never retro-gated.

Exit codes: ``0`` pass (including "no lintable path given"), ``1`` a touched plan lacks the record.
"""
from __future__ import annotations

import re
import sys

HEADER_RE = re.compile(r"(?mi)^#{2,4}\s+Design panel\b")
ENTRY_RE = re.compile(r"(?mi)^\s*[-*]\s*(ran|waived)\s*:\s*\S+")
RAN_RE = re.compile(r"(?mi)^\s*[-*]\s*ran\s*:\s*(?P<body>.+)$")
# "3 findings" / "1 finding" anywhere in the ran: body. Absent -> nothing to reconcile: a `ran:`
# that names no number is still a legitimate record of "the panel ran, nothing to report".
COUNT_RE = re.compile(r"(?i)\b(\d+)\s+finding")
# `- F3 REJECTED: reason`. The set is CLOSED so the record stays greppable across packs; the reason
# is required because a bare verdict tells the next reader nothing about why.
DISPOSITIONS = ("APPLIED", "REJECTED", "FLAGGED", "DEFERRED")
FINDING_RE = re.compile(
    r"(?m)^\s*[-*]\s*F(?P<n>\d+)\s+(?P<disp>" + "|".join(DISPOSITIONS) + r")\s*:\s*(?P<why>\S.*)$"
)
PLAN_PATH_RE = re.compile(r"^sut/[^/]+/plans/[^/]+\.md$")

HELP = (
    "add a `## Design panel` section with `- ran: <N> findings` plus one `- F<n> "
    "APPLIED|REJECTED|FLAGGED|DEFERRED: <reason>` line per finding, or `- waived: <reason>` — "
    "the Phase-2b design-review record (docs/multiagent/r-design.md). The dispositions are the "
    "GENERATOR's PROPOSAL; the HUMAN ratifies them at the spec-approval gate. There is no JUDGE at "
    "Phase 2b and no agent decides which findings are taken"
)


def check_text(text: str) -> str | None:
    """Return the failure reason for a plan body, or ``None`` if it passes."""
    if not HEADER_RE.search(text):
        return f"no `Design panel` section: {HELP}"
    if not ENTRY_RE.search(text):
        return f"`Design panel` section has no `ran:`/`waived:` entry: {HELP}"

    ran = RAN_RE.search(text)
    if ran is None:
        return None  # `waived:` only — a documented waiver needs no dispositions.
    count = COUNT_RE.search(ran.group("body"))
    if count is None:
        return None  # no declared count -> nothing to reconcile.

    declared = int(count.group(1))
    dispositions = FINDING_RE.findall(text)
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


def is_lintable_path(path: str) -> bool:
    """Only plans under a SUT plugin (``sut/<name>/plans/<file>.md``)."""
    return bool(PLAN_PATH_RE.match(path.replace("\\", "/")))


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
            failures.append(f"  [DESIGN-PANEL-RECORD-MISSING] {path} — {reason}")
    if failures:
        print("\n".join(failures))
        print(
            "\n  design-panel lint: a touched pack plan must record whether the Phase-2b design panel "
            "ran (R-DESIGN) or was waived, AND what was decided about each finding. The panel is "
            "advisory; this gates the RECORD, not the verdict — REJECTED passes like APPLIED, and a "
            "documented waiver passes."
        )
        return 1
    print("  design-panel lint: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
