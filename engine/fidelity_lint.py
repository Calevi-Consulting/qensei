"""Deterministic spec-fidelity lint — the forcing function behind "never weaken a spec".

The framework's prime invariant is that a test is never quietly relaxed to make a red gate
go green. An advisory LLM lens (agents/r-fidelity.md) *watches* for this, but a watcher is
not a gate — a documented rule without a forcing function is not reliably followed. This
is the gate: a mechanical AST diff of a changed pack case against its git
baseline that flags weakenings and exits non-zero (wire it as a pre-commit hook + in CI).

Detected weakenings (per RegressionCase, matched by class name):
  * a case CLASS was removed
  * persona changed (e.g. existing_data -> new_user drops durability)
  * tags / requires / covers SHRANK (coverage or pre-flight quietly narrowed)
  * severity DOWNGRADED (critical -> ... -> low)
  * the number of soft-assert calls DECREASED (assertions removed/loosened)
  * a skip/xfail escape hatch ADDED (decorator or truthy ``skip``/``xfail`` class attr)

A brand-new file (no git baseline) has nothing to weaken and is clean. Re-shaping a test
legitimately is allowed via ``--allow-reshape``, which downgrades shrink
findings to warnings so an intentional refactor is not blocked.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from dataclasses import dataclass

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_ASSERT_METHODS = frozenset(
    {"that", "equal", "not_equal", "approx", "contains", "is_none", "is_not_none", "is_true", "precondition"}
)


@dataclass
class Finding:
    path: str
    case: str
    rule: str
    detail: str
    severity: str = "block"  # "block" | "warn"


def _git_base(path: str, base_ref: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "show", f"{base_ref}:{path}"],
            capture_output=True, text=True, check=False,
        )
        return out.stdout if out.returncode == 0 else None
    except OSError:
        return None


def _cases(tree: ast.Module) -> dict[str, ast.ClassDef]:
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}


_COLLECTION_CTORS = {"frozenset", "set", "list", "tuple"}


def _eval_value(node):
    """literal_eval, but also unwrap ``frozenset({...})`` / ``set([...])`` constructor calls
    (``ast.literal_eval`` rejects those — yet packs declare ``tags = frozenset({...})``)."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _COLLECTION_CTORS:
        if not node.args:
            return []
        try:
            return list(ast.literal_eval(node.args[0]))
        except Exception:
            return None
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def _attr(cls: ast.ClassDef, name: str):
    for node in cls.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return _eval_value(node.value)
    return None


def _collection_len(cls, name) -> int | None:
    val = _attr(cls, name)
    if val is None:
        return None
    try:
        return len(val)
    except TypeError:
        return None


def _assert_count(cls: ast.ClassDef) -> int:
    n = 0
    for node in ast.walk(cls):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _ASSERT_METHODS:
                n += 1
    return n


def _has_skip(cls: ast.ClassDef) -> bool:
    for dec in cls.decorator_list:
        name = getattr(dec, "id", None) or getattr(getattr(dec, "func", None), "attr", "")
        if any(k in str(name).lower() for k in ("skip", "xfail")):
            return True
    for attr in ("skip", "xfail"):
        if _attr(cls, attr):
            return True
    return False


def lint_file(path: str, base_ref: str = "HEAD", allow_reshape: bool = False) -> list[Finding]:
    base_src = _git_base(path, base_ref)
    if base_src is None:
        return []  # new file (or untracked): nothing to weaken
    try:
        cur = ast.parse(open(path, encoding="utf-8").read())
        base = ast.parse(base_src)
    except SyntaxError as e:
        return [Finding(path, "?", "parse-error", f"could not parse: {e}")]

    cur_cases, base_cases = _cases(cur), _cases(base)
    findings: list[Finding] = []

    for name, b in base_cases.items():
        if "RegressionCase" not in _basenames(b) and not _attr(b, "id"):
            continue
        c = cur_cases.get(name)
        if c is None:
            findings.append(Finding(path, name, "case-removed", "a regression case was removed"))
            continue
        # persona
        bp, cp = _attr(b, "persona"), _attr(c, "persona")
        if bp and cp and bp != cp:
            findings.append(Finding(path, name, "persona-changed", f"persona {bp!r} -> {cp!r}"))
        # severity downgrade
        bs, cs = _attr(b, "severity"), _attr(c, "severity")
        if bs in _SEVERITY_RANK and cs in _SEVERITY_RANK and _SEVERITY_RANK[cs] < _SEVERITY_RANK[bs]:
            findings.append(Finding(path, name, "severity-downgraded", f"severity {bs} -> {cs}"))
        # shrank collections
        for coll in ("tags", "requires", "covers"):
            bl, cl = _collection_len(b, coll), _collection_len(c, coll)
            if bl is not None and cl is not None and cl < bl:
                findings.append(
                    Finding(path, name, f"{coll}-shrank", f"{coll} {bl} -> {cl} item(s)",
                            severity="warn" if allow_reshape else "block")
                )
        # fewer assertions
        ba, ca = _assert_count(b), _assert_count(c)
        if ca < ba:
            findings.append(
                Finding(path, name, "assertions-removed", f"soft-assert calls {ba} -> {ca}",
                        severity="warn" if allow_reshape else "block")
            )
        # skip/xfail added
        if _has_skip(c) and not _has_skip(b):
            findings.append(Finding(path, name, "skip-added", "a skip/xfail escape hatch was added"))

    return findings


def _basenames(cls: ast.ClassDef) -> set[str]:
    return {getattr(b, "id", getattr(b, "attr", "")) for b in cls.bases}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="qa-framework spec-fidelity lint")
    ap.add_argument("paths", nargs="*", help="pack case.py files (default: all sut/*/packs/*/case.py)")
    ap.add_argument("--base", default="HEAD", help="git ref to diff against (default HEAD)")
    ap.add_argument("--allow-reshape", action="store_true", help="downgrade shrink findings to warnings")
    args = ap.parse_args(argv)

    import glob

    paths = args.paths or sorted(glob.glob("sut/*/packs/*/case.py") + glob.glob("sut/*/ui-packs/*/case.py"))
    blocking = 0
    for p in paths:
        for f in lint_file(p, args.base, args.allow_reshape):
            tag = "BLOCK" if f.severity == "block" else "warn "
            print(f"  [{tag}] {f.path}::{f.case} — {f.rule}: {f.detail}")
            blocking += f.severity == "block"
    if blocking:
        print(f"\n  fidelity-lint: {blocking} weakening(s) — a spec must never be relaxed to go green.\n")
        return 1
    print("  fidelity-lint: no weakenings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
