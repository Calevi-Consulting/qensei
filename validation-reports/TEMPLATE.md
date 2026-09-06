# Validation Report — <change title>

**Date:** <YYYY-MM-DD>
**Spec:** <sut/<name>/specs/<id>.md, or "none — <why>">
**Branch:** <branch>
**Scope:** <one-line what changed>

## Phase 3 — Tests

| Check | Command | Result |
|---|---|---|
| Engine + gate units | `make test-engine` | <n passed> |
| Regression gate | `make test` | <n passed / skipped> |
| Fidelity lint | `make fidelity` | <no weakenings> |
| Secrets | `make secrets` | <clean> |

## Phase 4 — Code quality

- <dead code / duplication / encapsulation notes, or "none">

## Phase 5 — Security

- Secrets: <none added; mask() covers the log boundary>
- Deps: <pure stdlib — no CVE surface>

### Panel

<!-- The review-panel invocation record (docs/multiagent/review-panel.md § Invocation tiers).
     engine/panel_section_lint.py requires ONE of the two lines below in every touched report.
     Tier 1 (R-DIAGNOSIS as a subagent) runs on every non-green gate result; say what ran, or why
     nothing needed to. This template itself is out of the lint's scope. -->
- ran: <R-DIAGNOSIS tier 1 (<verdict>, flags …) · full panel: JUDGE <n BLOCK / n FIX / n FLAG>, digest in the PR>
- waived: <docs-only / tooling-only change · no non-green gate result this cycle>

## Phase 5.5 — Release safety

- **Rollback:** <revert commit / flag flip>. Changes are <additive?>.

## Result

<offline checks green; gate green on env(s) X / merge-readiness statement>
