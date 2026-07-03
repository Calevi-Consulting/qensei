"""Citation anti-fabrication gate — every file:line a lens cites must resolve.

A review lens (R-MECHANISM / R-EVIDENCE / R-COVERAGE) grounds a claim in a real file:line the
active SUT plugin exposes. Two anchor kinds, resolved identically:

  * ``sut/<name>/source/<rel>:<line>`` — the backend SOURCE (a source-backed SUT).
  * ``sut/<name>/{tickets,skills,learnings,specs}/<rel>:<line>`` — the ticket / docs, which are the
    contract of record for a SOURCELESS SUT (no readable source). This is the "ticket/doc snapshot":
    the committed in-repo ticket + docs the lens cites instead of source.

This gate resolves each citation against the real file:

  * file missing OR line out of range  -> FABRICATED  (exit 1: hard block)
  * a ``source/`` dir absent (e.g. a remote plugin with no clone) -> UNVERIFIABLE (exit 3)
  * resolves -> OK

A fabricated citation is a hard failure (the lens invented evidence). Only an absent ``source/``
clone is UNVERIFIABLE (not the lens's fault — no source to check against); ticket/doc anchors are
in-repo, so a miss there is FABRICATED like any other.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# sut/<name>/<contract-dir>/<rel-path>:<line> — contract-dir is the backend source or, for a
# sourceless SUT, the ticket/doc snapshot the lens cites instead. rel keeps the contract-dir.
_CITATION = re.compile(r"sut/([A-Za-z0-9_-]+)/((?:source|tickets|skills|learnings|specs)/[^\s:]+):(\d+)")


@dataclass
class Citation:
    raw: str
    sut: str
    rel: str
    line: int
    status: str  # OK | FABRICATED | UNVERIFIABLE
    detail: str = ""


def resolve_citations(text: str, repo_root: str = ".") -> list[Citation]:
    root = Path(repo_root)
    out: list[Citation] = []
    for m in _CITATION.finditer(text):
        raw, sut, rel, line = m.group(0), m.group(1), m.group(2), int(m.group(3))
        sut_dir = root / "sut" / sut
        f = sut_dir / rel
        # A source/ citation whose clone is absent is UNVERIFIABLE (not fabrication); ticket/doc
        # anchors are committed in-repo, so a miss there is a genuine FABRICATED.
        if rel.startswith("source/") and not (sut_dir / "source").exists():
            out.append(Citation(raw, sut, rel, line, "UNVERIFIABLE", "no source dir (remote plugin without a clone?)"))
        elif not f.exists():
            out.append(Citation(raw, sut, rel, line, "FABRICATED", "file does not exist"))
        else:
            with f.open(encoding="utf-8", errors="replace") as fh:
                n = sum(1 for _ in fh)
            if 1 <= line <= n:
                out.append(Citation(raw, sut, rel, line, "OK"))
            else:
                out.append(Citation(raw, sut, rel, line, "FABRICATED", f"line {line} out of range (file has {n})"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Qensei citation anti-fabrication gate")
    ap.add_argument("files", nargs="*", help="files to scan (default: stdin)")
    ap.add_argument("--root", default=".", help="repo root for resolving sut/<name>/source paths")
    args = ap.parse_args(argv)

    text = "".join(Path(f).read_text() for f in args.files) if args.files else sys.stdin.read()
    cites = resolve_citations(text, args.root)
    fabricated = [c for c in cites if c.status == "FABRICATED"]
    unverifiable = [c for c in cites if c.status == "UNVERIFIABLE"]
    for c in cites:
        if c.status != "OK":
            print(f"  [{c.status}] {c.raw} — {c.detail}")
    if not cites:
        print("  citation-gate: no citations found.")
        return 0
    if fabricated:
        print(f"\n  citation-gate: {len(fabricated)} fabricated citation(s) — a lens invented evidence.\n")
        return 1
    if unverifiable:
        print(f"  citation-gate: {len(unverifiable)} unverifiable (no source) — not fabricated.")
        return 3
    print(f"  citation-gate: {len(cites)} citation(s) all resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
