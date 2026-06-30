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
  * tags        — selection markers ({"smoke", "slow", "isolated", ...}); the runner
                  filters on a tag expression so the gate can run lanes (see selection.py)
  * severity    — "critical" | "high" | "medium" | "low" (declarative; for report grouping)
  * requires    — pre-flight requirement keys the target backend must satisfy, else the
                  case skips (partial) or fails (block) — see preflight.py

A case may override ``teardown(self, sut)`` to remove anything it created on a shared
backend; the runner calls it best-effort in a ``finally`` (so a new_user case self-cleans
even if its body raised).

Assertions are SOFT (collected) so one run reports every break. A genuine PRECONDITION
("the object I need was created") should be a hard ``require(...)`` / ``raise
PreconditionError`` — the runner reports that as a real failure, NOT as transient infra.
"""
from __future__ import annotations

from dataclasses import dataclass


class PreconditionError(AssertionError):
    """A hard precondition that must hold before the soft checks are meaningful.

    Distinct from an arbitrary exception (infra/transient): a raised PreconditionError is
    a real test verdict, so diagnostics does NOT misclassify it as ENV_OR_TRANSIENT.
    """


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

    def not_equal(self, actual, unexpected, label):
        return self.that(
            actual != unexpected, f"{label}: expected != {unexpected!r}, got {actual!r}"
        )

    def approx(self, actual, expected, label, tol=1e-9):
        return self.that(
            abs(actual - expected) <= tol,
            f"{label}: expected ~{expected!r}, got {actual!r}",
        )

    def contains(self, container, member, label):
        return self.that(
            member in (container or []), f"{label}: expected {member!r} in {container!r}"
        )

    def is_none(self, actual, label):
        return self.that(actual is None, f"{label}: expected None, got {actual!r}")

    def is_not_none(self, actual, label):
        return self.that(actual is not None, f"{label}: expected a value, got None")

    def is_true(self, actual, label):
        return self.that(bool(actual), f"{label}: expected truthy, got {actual!r}")

    def precondition(self, ok, detail):
        """A HARD gate: raises :class:`PreconditionError` if ``ok`` is false."""
        if not ok:
            raise PreconditionError(detail)
        return True

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
    tags = frozenset()
    severity = "medium"
    requires = []

    def run(self, sut, expect):  # noqa: D401 - implemented by concrete packs
        raise NotImplementedError

    def teardown(self, sut):  # noqa: D401 - overridden by cases that create durable state
        """Best-effort cleanup of anything this case created. Default: no-op."""
        return None
