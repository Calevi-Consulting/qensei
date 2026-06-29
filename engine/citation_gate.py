"""Citation anti-fabrication gate — every source:line a lens cites must resolve.

A review lens (R-MECHANISM / R-EVIDENCE) grounds a claim in the backend source as
``sut/<name>/source/<rel>:<line>``. This gate resolves each citation against the real file:

  * file missing OR line out of range  -> FABRICATED  (exit 1: hard block)
  * source dir absent (e.g. a remote plugin with no clone) -> UNVERIFIABLE (exit 3)
  * resolves -> OK

A fabricated citation is treated as a hard failure (the lens invented evidence); an
unverifiable one is reported distinctly (not the lens's fault — no source to check against)
via a separate exit code.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# sut/<name>/source/<rel-path>:<line>
_CITATION = re.compile(r"sut/([A-Za-z0-9_-]+)/source/([^\s:]+):(\d+)")


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
        source_dir = root / "sut" / sut / "source"
        f = source_dir / rel
        if not source_dir.exists():
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
        print("  citation-gate: no source citations found.")
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
