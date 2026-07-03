"""design — backend-aware test-case DESIGN (the manual-QA design capability, made generic).

Reads the backend's declared surface from the source (ROUTES + BUSINESS_RULES via
the SUTConnector) and cross-references it against what the existing packs cover
(their `covers` declarations), to report coverage gaps and propose candidate cases.

This is "design/improve test cases from the backend": the framework knows the
system's surface because it can read the source, and knows what is tested because
it can read the packs — so it can propose the difference.
"""
from __future__ import annotations

from engine import runner
from engine.ui import discover_ui_cases


def coverage(sut, packs_dir):
    covered = set()
    for case_cls in runner.discover_cases(packs_dir):
        covered.update(getattr(case_cls, "covers", []))
    # UI packs cover the same declared surface through the front-end — count them too.
    for case_cls in discover_ui_cases(str(sut.ui_packs_dir)):
        covered.update(getattr(case_cls, "covers", []))

    # Sourceless SUT: there is no backend source to read, so the declared surface is unknown
    # here — it is defined by the ticket + docs. Report what the packs cover; never invent
    # phantom "gaps" (or a misleading "no gaps") against a surface we cannot see.
    if not sut.has_source:
        return {
            "has_source": False,
            "routes": [],
            "rules": [],
            "covered": sorted(covered),
            "route_gaps": [],
            "rule_gaps": [],
        }

    src = sut.source_module()
    routes = [f"{m} {p}" for m, p, _ in getattr(src, "ROUTES", [])]
    rules = [r["id"] for r in getattr(src, "BUSINESS_RULES", [])]
    route_gaps = [r for r in routes if r not in covered]
    rule_gaps = [r for r in rules if r not in covered]
    return {
        "has_source": True,
        "routes": routes,
        "rules": rules,
        "covered": sorted(covered),
        "route_gaps": route_gaps,
        "rule_gaps": rule_gaps,
    }


def print_design_report(sut, packs_dir):
    c = coverage(sut, packs_dir)
    if not c.get("has_source", True):
        print(f"\n  DESIGN report — '{sut.name}' is SOURCELESS (no backend source to read)\n")
        print("  the backend surface is defined by the ticket + docs, not read from source, so")
        print("  coverage-gap analysis against the backend surface is unavailable in this mode.")
        print("  covered by existing packs: " + (", ".join(c["covered"]) or "(none)"))
        print("\n  to design cases here, work from the ticket's acceptance criteria + product docs")
        print("  (sut/<name>/skills/); DESIGN cannot enumerate endpoints/rules it cannot read.\n")
        return c
    print(f"\n  DESIGN report — backend surface of '{sut.name}' (read from {sut.source_path()})\n")
    print(f"  endpoints ({len(c['routes'])}): " + ", ".join(c["routes"]))
    print(f"  business rules ({len(c['rules'])}): " + (", ".join(c["rules"]) or "(none)"))
    print("  covered by packs: " + (", ".join(c["covered"]) or "(none)"))
    if c["route_gaps"] or c["rule_gaps"]:
        print("\n  COVERAGE GAPS — candidate cases to design:")
        for r in c["route_gaps"]:
            print(f"    - endpoint not regressed: {r}  -> propose a "
                  "new_user case asserting its happy path + one negative")
        for r in c["rule_gaps"]:
            print(f"    - business rule not regressed: {r}  -> propose a case pinning the rule's contract value")
    else:
        print("\n  no gaps — every endpoint and business rule has a regression.")
    print()
    return c


def main(argv=None):
    import argparse

    from engine.sut import SUTConnector

    ap = argparse.ArgumentParser(description="Qensei backend-aware test-case design")
    ap.add_argument("--sut", required=True)
    ap.add_argument("--packs", default=None, help="packs dir (default: the SUT's own packs dir)")
    args = ap.parse_args(argv)
    sut = SUTConnector(args.sut)  # design reads source only; no runtime needed
    print_design_report(sut, args.packs or str(sut.packs_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
