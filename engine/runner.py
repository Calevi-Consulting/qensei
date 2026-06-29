"""runner — the deterministic regression GATE.

Discovers cases under packs/, runs each against a started SUT, prints a report,
and reports pass/fail. This is the framework's analog of a merge gate: green is
a precondition to landing. Each case runs from a clean state (cart cleared) to
keep the new_user persona isolated.
"""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from engine.case import Expect, RegressionCase


def _load_module(case_file):
    case_file = Path(case_file)
    spec = importlib.util.spec_from_file_location(
        f"pack_{case_file.parent.name}", case_file
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cases_in(mod):
    found = []
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        if issubclass(obj, RegressionCase) and obj is not RegressionCase:
            found.append(obj)
    return found


def discover_cases(packs_dir):
    """All RegressionCase subclasses in packs_dir/*/case.py."""
    cases = []
    for case_file in sorted(Path(packs_dir).glob("*/case.py")):
        cases.extend(_cases_in(_load_module(case_file)))
    return cases


def load_pack_case(pack_dir):
    """The first RegressionCase in a single pack directory (pack_dir/case.py)."""
    cases = _cases_in(_load_module(Path(pack_dir) / "case.py"))
    if not cases:
        raise ValueError(f"no RegressionCase found in {pack_dir}")
    return cases[0]


def run_case(case_cls, sut):
    case = case_cls()
    expect = Expect()
    sut.post("/cart/clear")  # isolation: new_user persona starts ephemeral
    error = None
    try:
        case.run(sut, expect)
    except Exception as e:  # a thrown case is an infra/test error, not a soft check
        error = repr(e)
    return case, expect, error


def run_packs(sut, packs_dir):
    cases = discover_cases(packs_dir)
    print(f"\n  qa-framework gate — {len(cases)} case(s) vs '{sut.name}' @ {sut.base_url}\n")
    results = []
    for case_cls in cases:
        case, expect, error = run_case(case_cls, sut)
        ok = expect.passed and not error
        print(
            f"  [{'PASS' if ok else 'FAIL'}] {case.id} — {case.title} "
            f"(persona={case.persona}, spec={case.spec_ref})"
        )
        for f in expect.failures:
            print(f"         x {f.detail}")
        if error:
            print(f"         x ERROR {error}")
        results.append((case, expect, error, ok))
    passed = sum(1 for *_, ok in results if ok)
    print(f"\n  {passed}/{len(results)} passed\n")
    return results
