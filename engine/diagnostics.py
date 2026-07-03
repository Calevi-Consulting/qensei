"""diagnostics — the failure-triage lens (the generic R-DIAGNOSIS / R-PLATFORM).

When a case fails, the central question is: is this a TEST_BUG (the test is wrong,
fix the test — never weaken the spec) or a REAL_BUG (the system regressed, keep the
test red and file a bug)? Answering it requires reading the BACKEND CONTRACT, which
is exactly why the framework has backend source access.

Heuristic (deliberately simple but principled):
  * the case throws / network error  -> ENV_OR_TRANSIENT
  * the SUT is sourceless (no BUSINESS_RULES oracle) -> INDETERMINATE (contract of record = ticket)
  * the case has no contract_claim    -> INDETERMINATE (needs a human)
  * claim disagrees with the source contract -> TEST_BUG
  * claim agrees with the source contract but the running system violated it -> REAL_BUG

This is the same triage a mature regression suite applies by hand; here it is made
explicit and grounded in the source the SUTConnector exposes.
"""
from __future__ import annotations

from engine import runner


def _rules_index(sut):
    src = sut.source_module()
    return {r["id"]: r for r in getattr(src, "BUSINESS_RULES", [])}


def diagnose(case_cls, sut):
    case, expect, error = runner.run_case(case_cls, sut)

    if expect.passed and not error:
        return {
            "verdict": "NO_FAILURE",
            "case": case.id,
            "why": "the case passed against the running system; nothing to triage.",
        }

    if error and getattr(case, "_precondition_failed", False):
        return {
            "verdict": "PRECONDITION_FAILED",
            "case": case.id,
            "evidence": error,
            "why": (
                "a hard precondition the case declared did not hold — this is a REAL test "
                "verdict (the setup the contract depends on is absent), not transient infra. "
                "Adjudicate as REAL_BUG vs TEST_BUG; do NOT dismiss it as a flake."
            ),
        }

    if error:
        return {
            "verdict": "ENV_OR_TRANSIENT",
            "case": case.id,
            "evidence": error,
            "why": "the case raised before completing — infrastructure/environment, not a contract verdict.",
        }

    claim = getattr(case, "contract_claim", None)
    failures = [f.detail for f in expect.failures]

    # Sourceless SUT: no BUSINESS_RULES oracle. REAL_BUG vs TEST_BUG cannot be decided
    # mechanically — the ticket is BOTH the test's origin and the contract of record, so an
    # independent judgment is impossible. The deterministic lens stays honest and defers; it
    # never guesses a REAL/TEST verdict here. (Phase B retargets citations to the ticket/docs.)
    if not sut.has_source:
        return {
            "verdict": "INDETERMINATE",
            "case": case.id,
            "failures": failures,
            "contract_claim": claim,
            "contract_of_record": "ticket",
            "why": (
                "the SUT is sourceless — there is no backend contract (BUSINESS_RULES) to compare "
                "the claim against, so REAL_BUG vs TEST_BUG cannot be decided mechanically. The "
                "contract of record is the ticket/docs; the review panel and the human must "
                "adjudicate (a wrong ticket cannot be ruled out here)."
            ),
        }

    rules = _rules_index(sut)
    if not claim or claim.get("rule") not in rules:
        return {
            "verdict": "INDETERMINATE",
            "case": case.id,
            "failures": failures,
            "why": "no contract_claim resolvable against the backend source — a human must adjudicate.",
        }

    rule = rules[claim["rule"]]
    contract_rate = rule.get("rate")
    claimed_rate = claim.get("rate")
    source_path = str(sut.source_path())

    if claimed_rate is not None and abs(claimed_rate - contract_rate) > 1e-9:
        return {
            "verdict": "TEST_BUG",
            "case": case.id,
            "rule": rule["id"],
            "failures": failures,
            "source": source_path,
            "why": (
                f"the test asserts rate={claimed_rate} but the backend contract "
                f"(BUSINESS_RULES['{rule['id']}'] in the source) is rate={contract_rate}. "
                f"The spec intent is not weakened — fix the test's expectation."
            ),
        }

    return {
        "verdict": "REAL_BUG",
        "case": case.id,
        "rule": rule["id"],
        "failures": failures,
        "source": source_path,
        "why": (
            f"the test's expectation matches the backend contract (rate={contract_rate}) "
            f"but the running system violated it. The platform regressed — keep the test "
            f"red and file a bug; do NOT change the test."
        ),
    }


def print_diagnosis(d):
    print(f"\n  DIAGNOSIS for {d['case']}: {d['verdict']}")
    if d.get("failures"):
        for f in d["failures"]:
            print(f"         observed: {f}")
    if d.get("source"):
        print(f"         contract source: {d['source']}")
    print(f"         -> {d['why']}\n")
