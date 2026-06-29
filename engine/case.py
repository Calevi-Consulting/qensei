"""RegressionCase — the unit of regression coverage.

A case encodes a BEHAVIORAL CONTRACT (what the system does for the user), not an
internal call sequence. It declares:

  * id          — stable identifier (usually the ticket id + slug)
  * spec_ref    — the intent spec it satisfies (core/specs/<id>.md)
  * persona     — "new_user" (ephemeral) or "existing_data" (durable) — see policies
  * covers      — the backend surface it exercises (endpoints + business-rule ids),
                  read by the DESIGN layer to compute coverage gaps
  * contract_claim — the business-rule value the case relies on, read by the
                  DIAGNOSTICS layer to tell REAL_BUG from TEST_BUG against the source

Assertions are SOFT (collected) so one run reports every break, mirroring the
soft-expect pattern of a mature regression suite.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    ok: bool
    detail: str


class Expect:
    """Soft assertions — collect all failures instead of stopping at the first."""

    def __init__(self):
        self.checks = []

    def that(self, ok, detail):
        self.checks.append(CheckResult(bool(ok), detail))
        return bool(ok)

    def equal(self, actual, expected, label):
        return self.that(
            actual == expected, f"{label}: expected {expected!r}, got {actual!r}"
        )

    def approx(self, actual, expected, label, tol=1e-9):
        return self.that(
            abs(actual - expected) <= tol,
            f"{label}: expected ~{expected!r}, got {actual!r}",
        )

    @property
    def failures(self):
        return [c for c in self.checks if not c.ok]

    @property
    def passed(self):
        return not self.failures


class RegressionCase:
    id = "UNNAMED"
    title = ""
    spec_ref = None
    persona = "new_user"
    covers = []
    contract_claim = None

    def run(self, sut, expect):  # noqa: D401 - implemented by concrete packs
        raise NotImplementedError
