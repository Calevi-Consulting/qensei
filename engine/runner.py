"""runner — the deterministic regression GATE.

Discovers cases under the active SUT's packs dir (sut/<name>/packs/), optionally filters
them by a tag expression, evaluates each
case's pre-flight requirements against the target backend (skip-or-block), runs the rest
from a clean state, calls best-effort teardown, prints a report, and reports pass/fail.
This is the framework's analog of a merge gate: green is a precondition to landing.

A case's clean-state reset comes from ``sut.isolate()`` (a plugin/manifest hook), NOT a
hardcoded backend endpoint — the runner is product-neutral.
"""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from engine import preflight as preflight_mod
from engine import selection
from engine.case import Expect, PreconditionError, RegressionCase


def _load_module(case_file):
    case_file = Path(case_file)
    spec = importlib.util.spec_from_file_location(f"pack_{case_file.parent.name}", case_file)
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
    """Run one case from a clean state; teardown best-effort in a finally.

    Returns ``(case, expect, error)``. ``error`` is None, a ``"PRECONDITION: ..."`` string
    (a real verdict — ``case._precondition_failed`` is set), or an exception repr (transient).
    """
    case = case_cls()
    expect = Expect()
    case._precondition_failed = False
    sut.isolate()  # clean state (plugin/manifest hook), not a hardcoded endpoint
    error = None
    try:
        case.run(sut, expect)
    except PreconditionError as e:
        error = f"PRECONDITION: {e}"
        case._precondition_failed = True
    except Exception as e:  # a thrown case is an infra/test error, not a soft check
        error = repr(e)
    finally:
        try:
            case.teardown(sut)
        except Exception as e:  # cleanup must never abort the run
            print(f"         ~ teardown error (ignored): {e!r}")
    return case, expect, error


def run_packs(sut, packs_dir, select=None, preflight="partial"):
    """Run the gate. ``select`` is a tag expression (None = all); ``preflight`` is
    'partial' (skip unmet) or 'block' (fail unmet). Returns
    ``[(case, expect, error, status)]`` with status PASS / FAIL / SKIP."""
    cases = [c for c in discover_cases(packs_dir) if selection.matches(getattr(c, "tags", ()), select)]
    registry = preflight_mod.default_registry(sut)
    lane = f" [{select}]" if select else ""
    print(f"\n  qa-framework gate{lane} — {len(cases)} case(s) vs '{sut.name}' @ {sut.base_url}\n")

    results = []
    for case_cls in cases:
        unmet = preflight_mod.evaluate(case_cls, sut, registry)
        if unmet:
            reason = "; ".join(f"{u.key} ({u.reason})" for u in unmet)
            if preflight == "partial":
                case = case_cls()
                case._skip_reason = reason
                print(f"  [SKIP] {case_cls.id} — unmet: {reason}")
                results.append((case, Expect(), None, "SKIP"))
                continue
            # block: fail the case without running it
            case, expect = case_cls(), Expect()
            expect.that(False, f"unmet pre-flight requirement(s): {reason}")
            results.append((case, expect, None, "FAIL"))
            print(f"  [FAIL] {case_cls.id} — blocked on unmet requirement: {reason}")
            continue

        case, expect, error = run_case(case_cls, sut)
        status = "PASS" if (expect.passed and not error) else "FAIL"
        print(
            f"  [{status}] {case.id} — {case.title} "
            f"(persona={case.persona}, severity={case.severity}, spec={case.spec_ref})"
        )
        for f in expect.failures:
            print(f"         x {f.detail}")
        if error:
            print(f"         x {error}")
        results.append((case, expect, error, status))

    passed = sum(1 for r in results if r[3] == "PASS")
    skipped = sum(1 for r in results if r[3] == "SKIP")
    failed = sum(1 for r in results if r[3] == "FAIL")
    print(f"\n  {passed} passed, {failed} failed, {skipped} skipped (of {len(results)})\n")
    return results
