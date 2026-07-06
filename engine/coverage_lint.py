"""Deterministic coverage-metadata gate — the forcing function behind "a pack's declared
coverage must match its README and resolve against the SUT".

The framework's other gates share a blind spot for a **brand-new pack**: ``fidelity_lint`` is an
AST diff against the git baseline, so a file with no blob at ``HEAD`` has nothing to weaken and is
clean; ``design.py`` only computes the coverage gap *forward* (source routes/rules no pack covers)
and never checks the reverse direction, nor opens the pack's README/spec. The only component that
cross-checks ``covers`` / ``contract_claim`` against the source and the README is the **advisory**
``r-coverage`` lens — which never gates a merge. So a new pack whose ``case.py`` diverges from its
own README/spec (a copy-paste with a stale ``covers`` list) sails through CI green.

This is the deterministic companion the ``agents/r-coverage.md`` lens reserves by name. It runs on
**every** pack with **no git baseline**, and BLOCKs when the declared coverage metadata is internally
inconsistent, dangling, or (on a source-backed SUT) unresolvable against the SUT source.

Scope — symptom, not disease. This gate blocks the *covers-drift artifact* (a ``covers`` list that
disagrees with the README, or resolves to nothing). It does NOT decide whether ``run()`` exercises
the behaviour the spec's acceptance criteria describe — that is inherently semantic and stays with
the ``r-coverage`` lens + a human. The gate raises the floor; it does not replace the lens.

Detected violations (per case class):
  * ``covers-inconsistent``       — ``case.py`` ``covers`` set != the README ``Covers:`` set   (BLOCK)
  * ``cover-unresolved``          — a ``covers`` token resolves to no ROUTE / rule id   (BLOCK, sourced only)
  * ``contract_claim-unresolved`` — ``contract_claim.rule`` is not a BUSINESS_RULES id   (BLOCK, sourced only)
  * ``contract_claim-malformed``  — ``contract_claim`` is declared but is not a dict   (BLOCK)
  * ``spec_ref-missing`` / ``-dangling`` / ``-misplaced`` — no / missing / outside-the-SUT spec   (BLOCK)
  * ``readme-covers-missing``     — the README has no parseable ``Covers:`` line   (BLOCK)
  * ``source-load-error``         — a source-backed SUT's source will not import   (BLOCK, sourced only)
  * ``duplicate-run-body``        — a ``run()`` body verbatim (modulo docstring) to another pack's   (WARN)

Sourceless SUTs (``has_source`` False): the source-backed checks (cover / contract_claim resolution)
are SKIPPED and reported ``UNVERIFIED`` — never FAIL. The source-independent checks (consistency,
``spec_ref`` resolves, README ``Covers:`` present) still run and still gate.

Exit codes: ``0`` pass (WARN alone still passes), ``1`` any BLOCK, ``2`` no packs discovered (the
false-green-guard convention — an empty run must never look like a pass).
"""
from __future__ import annotations

import argparse
import ast
import glob
import os
import re
import sys
from pathlib import Path

from engine.fidelity_lint import Finding, _attr, _basenames, _cases
from engine.sut import SUTConnector

# The README "Covers:" line, tolerating BOTH observed authoring styles so the parser never bakes one
# SUT's house style into the product-neutral engine/:
#     - Covers: `POST /cart`, `GET /cart`
#     - **Covers:** `POST /widgets`, `GET /widgets/{id}`
_COVERS_LINE = re.compile(r"^\s*-\s*\*{0,2}\s*Covers\s*[:*]*\s*(.*)$")
_BACKTICK = re.compile(r"`([^`]+)`")

_CASE_BASES = frozenset({"RegressionCase", "UICase"})


def _is_case_class(cls: ast.ClassDef) -> bool:
    """A concrete regression/UI case: it subclasses (Regression|UI)Case or declares an ``id``."""
    return bool(_CASE_BASES & _basenames(cls)) or _attr(cls, "id") is not None


def _case_classes(tree: ast.Module) -> list[ast.ClassDef]:
    return [c for c in _cases(tree).values() if _is_case_class(c)]


def _readme_covers(readme_path: Path) -> set[str] | None:
    """The README ``Covers:`` line as a set of tokens, or ``None`` if there is no parseable line."""
    if not readme_path.exists():
        return None
    for line in readme_path.read_text(encoding="utf-8").splitlines():
        m = _COVERS_LINE.match(line)
        if m:
            toks = set(_BACKTICK.findall(m.group(1)))
            if toks:
                return toks  # first Covers line that actually carries backtick tokens
            # a prose "Covers ..." bullet with no tokens is not the metadata line — keep scanning
    return None  # no Covers line yielded any backtick token


def _run_body_fingerprint(cls: ast.ClassDef) -> str | None:
    """Structural fingerprint of the case's ``run()`` body (docstring stripped) — two packs with a
    near-verbatim ``run()`` body yield the same fingerprint (the copy-paste signal)."""
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            body = list(node.body)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(getattr(body[0], "value", None), ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]  # drop the docstring so it does not defeat the match
            if not body:
                return None
            return ast.dump(ast.Module(body=body, type_ignores=[]))
    return None


def _sut_for(pack_dir: Path, cache: dict) -> SUTConnector:
    # sut/<name>/packs/<id>/  ->  sut/<name>   (same shape for ui-packs/)
    sut_root = pack_dir.parent.parent
    key = str(sut_root)
    if key not in cache:
        cache[key] = SUTConnector(sut_root)
    return cache[key]


def _valid_tokens(sut: SUTConnector, cache: dict) -> tuple[set[str], set[str]]:
    """(routes, rules) declared by the SUT source, read ONLY through the SUTConnector (R0)."""
    key = str(sut.dir)
    if key not in cache:
        src = sut.source_module()
        routes = {f"{m} {p}" for m, p, *_ in getattr(src, "ROUTES", [])}
        rules = {r["id"] for r in getattr(src, "BUSINESS_RULES", [])}
        cache[key] = (routes, rules)
    return cache[key]


def lint_pack(
    pack_dir: Path, sut_cache: dict, src_cache: dict
) -> tuple[list[Finding], list[str], list[tuple[str, str]]]:
    """Findings, ``UNVERIFIED`` info lines, and ``(label, run-body fingerprint)`` pairs for one pack."""
    findings: list[Finding] = []
    infos: list[str] = []
    fingerprints: list[tuple[str, str]] = []
    case_file = pack_dir / "case.py"
    rel = os.path.relpath(case_file)

    try:
        tree = ast.parse(case_file.read_text(encoding="utf-8"))
    except (SyntaxError, OSError) as e:
        return [Finding(rel, "?", "parse-error", f"could not parse: {e}")], infos, fingerprints

    try:
        sut = _sut_for(pack_dir, sut_cache)
    except Exception as e:  # a malformed/missing manifest is a real, blocking defect
        return [Finding(rel, "?", "sut-load-error", f"could not load the SUT manifest: {e}")], infos, fingerprints

    readme_covers = _readme_covers(pack_dir / "README.md")

    for cls in _case_classes(tree):
        cid = _attr(cls, "id") or cls.name
        raw_covers = _attr(cls, "covers")
        covers = set(raw_covers) if raw_covers else set()
        spec_ref = _attr(cls, "spec_ref")

        # contract_claim, when declared, must be a dict with a 'rule' key. A non-dict literal
        # (e.g. a bare string) would otherwise fail OPEN — silently skipped — letting a bogus rule
        # reach diagnose. A None/absent claim is fine (no claim).
        contract_claim = _attr(cls, "contract_claim")
        if contract_claim is not None and not isinstance(contract_claim, dict):
            findings.append(Finding(rel, cid, "contract_claim-malformed",
                                    f"contract_claim must be a dict with a 'rule' key, "
                                    f"got {type(contract_claim).__name__}"))
            contract_claim = None

        # R6 — README Covers line present + parseable; R2 — covers-consistency (BLOCK)
        if readme_covers is None:
            findings.append(Finding(rel, cid, "readme-covers-missing",
                                    "the README has no parseable `Covers:` line"))
        elif covers != readme_covers:
            only_case = sorted(covers - readme_covers) or ["-"]
            only_readme = sorted(readme_covers - covers) or ["-"]
            findings.append(Finding(rel, cid, "covers-inconsistent",
                                    f"case.py covers != README Covers "
                                    f"(only in case.py: {only_case}; only in README: {only_readme})"))

        # R5 — spec_ref resolves to a spec under THIS SUT's specs dir
        if not spec_ref:
            findings.append(Finding(rel, cid, "spec_ref-missing", "case declares no spec_ref"))
        else:
            sp = Path(spec_ref)
            if not sp.exists():
                findings.append(Finding(rel, cid, "spec_ref-dangling",
                                        f"spec_ref points to a missing file: {spec_ref}"))
            elif not sp.resolve().is_relative_to(sut.specs_dir.resolve()):
                findings.append(Finding(rel, cid, "spec_ref-misplaced",
                                        f"spec_ref {spec_ref!r} does not resolve under "
                                        f"{sut.name}'s specs dir"))

        # R3 / R4 — validity + contract_claim resolution, source-backed only (R7 degradation)
        if sut.has_source:
            try:
                routes, rules = _valid_tokens(sut, src_cache)
            except Exception as e:  # a source that will not import is a real, blocking defect
                findings.append(Finding(rel, cid, "source-load-error",
                                        f"could not read {sut.name} source: {e}"))
                fp = _run_body_fingerprint(cls)
                if fp:
                    fingerprints.append((f"{rel}::{cid}", fp))
                continue
            valid = routes | rules
            for tok in sorted(covers):
                if tok not in valid:
                    findings.append(Finding(rel, cid, "cover-unresolved",
                                            f"covers token {tok!r} resolves to no ROUTE or "
                                            f"BUSINESS_RULES id in {sut.name} source"))
            if isinstance(contract_claim, dict) and contract_claim.get("rule"):
                if contract_claim["rule"] not in rules:
                    findings.append(Finding(rel, cid, "contract_claim-unresolved",
                                            f"contract_claim rule {contract_claim['rule']!r} is not "
                                            f"in {sut.name} BUSINESS_RULES"))
        else:
            for tok in sorted(covers):
                infos.append(f"  [UNVERIFIED] {rel}::{cid} — cover {tok!r} unresolved "
                             f"(SUT {sut.name!r} is sourceless)")
            if isinstance(contract_claim, dict) and contract_claim.get("rule"):
                infos.append(f"  [UNVERIFIED] {rel}::{cid} — contract_claim unresolved "
                             f"(SUT {sut.name!r} is sourceless)")

        fp = _run_body_fingerprint(cls)
        if fp:
            fingerprints.append((f"{rel}::{cid}", fp))

    return findings, infos, fingerprints


def _default_pack_dirs() -> list[Path]:
    """Every pack in the tree, discovered through each SUT's DECLARED packs_dir / ui_packs_dir (R0)
    rather than the literal ``packs``/``ui-packs`` names, so a SUT that customises tests.packs is not
    silently skipped. Falls back to the default names for a manifest that will not load (its packs
    then surface a ``sut-load-error`` in lint_pack)."""
    dirs: list[Path] = []
    for mpath in sorted(glob.glob("sut/*/manifest.json")):
        sut_root = Path(mpath).parent
        try:
            sut = SUTConnector(sut_root)
            bases = [sut.packs_dir, sut.ui_packs_dir]
        except Exception:
            bases = [sut_root / "packs", sut_root / "ui-packs"]
        for base in bases:
            for case_file in sorted(base.glob("*/case.py")):
                dirs.append(case_file.parent)
    return dirs


def _pack_dirs(paths: list[str]) -> list[Path]:
    """Pack dirs to check. Given explicit paths (case.py / README.md / a pack dir), map each to its
    pack dir; otherwise discover every pack in the tree via each SUT's declared dirs."""
    if not paths:
        return _default_pack_dirs()
    dirs: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        pp = Path(p)
        d = pp if pp.is_dir() else pp.parent
        if (d / "case.py").exists() and str(d) not in seen:
            seen.add(str(d))
            dirs.append(d)
    return dirs


def _duplicate_findings(fingerprints: list[tuple[str, str]]) -> list[Finding]:
    """R8 — WARN (never BLOCK) when two packs share a near-verbatim ``run()`` body."""
    by_fp: dict[str, list[str]] = {}
    for label, fp in fingerprints:
        by_fp.setdefault(fp, []).append(label)
    out: list[Finding] = []
    for labels in by_fp.values():
        if len(labels) > 1:
            for label in labels:
                others = [x for x in labels if x != label]
                path, case = label.split("::", 1)
                out.append(Finding(path, case, "duplicate-run-body",
                                   f"run() body is near-identical to: {', '.join(others)}",
                                   severity="warn"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Qensei coverage-metadata gate")
    ap.add_argument("paths", nargs="*",
                    help="pack case.py/README.md files or pack dirs (default: all packs in sut/*)")
    args = ap.parse_args(argv)

    pack_dirs = _pack_dirs(args.paths)
    if not pack_dirs:
        # false-green-guard convention: an empty run must never look like a pass.
        print("  coverage-lint: no packs discovered — nothing to check (did the path glob match?).")
        return 2

    sut_cache: dict = {}
    src_cache: dict = {}
    all_findings: list[Finding] = []
    all_infos: list[str] = []
    all_fps: list[tuple[str, str]] = []
    for d in pack_dirs:
        f, i, fp = lint_pack(d, sut_cache, src_cache)
        all_findings += f
        all_infos += i
        all_fps += fp
    all_findings += _duplicate_findings(all_fps)

    for info in all_infos:
        print(info)
    blocking = 0
    for f in all_findings:
        tag = "BLOCK" if f.severity == "block" else "warn "
        print(f"  [{tag}] {f.path}::{f.case} — {f.rule}: {f.detail}")
        blocking += f.severity == "block"

    if blocking:
        print(f"\n  coverage-lint: {blocking} coverage-metadata violation(s) — a pack's declared "
              "coverage must match its README and resolve against the SUT.\n")
        return 1
    warns = sum(1 for f in all_findings if f.severity == "warn")
    tail = f" ({warns} warning(s))." if warns else "."
    print(f"  coverage-lint: no coverage-metadata violations{tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
