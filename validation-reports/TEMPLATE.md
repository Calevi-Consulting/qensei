# Validation Report — <change title>

**Date:** <YYYY-MM-DD>
**Spec:** <core/specs/<id>.md, or "none — <why>">
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

## Phase 5.5 — Release safety

- **Rollback:** <revert commit / flag flip>. Changes are <additive?>.

## Result

<offline checks green; gate green on env(s) X / merge-readiness statement>
