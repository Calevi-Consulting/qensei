# Validation Report — a seeded gate red declares itself

**Date:** 2026-09-06
**Spec:** none — a defect fix tracked as [#41](https://github.com/Calevi-Consulting/qensei/issues/41).
The finding came out of the spec-005 PR-2 orchestrator run, not from a spec of its own.
**Branch:** `fix/seeded-red-provenance`
**Scope:** the gate and its report now record whether a run had a fault seeded into the SUT.

## The defect

`--seed-bug` injects a fault so the framework can demonstrate REAL_BUG detection. It is a flag on the
**gate binary** (`engine/run.py`), not only on the diagnostics entry point — and nothing recorded it. A
seeded run produced exit 1, a failing `<testcase>`, and a JUnit/JSON artifact byte-indistinguishable from a
genuine regression, for any SUT. Every other control in this repo defers to the gate as the single source of
truth for "green"; an artifact that can be manufactured undermines the one signal the rest rely on.

Not hypothetical: the run that found it was handed a brief asserting "gate red on sut/mock-shop", and the red
existed only because the brief's own flag put it there. The panel caught it by re-running the gate instead of
trusting the claim. A human handed the JUnit rather than the claim would have had no defence.

## What changed

- **`engine/sut.py`** — `SUTConnector.seeded` records whether seeding **actually applied**. Only an
  `in_process` runtime has a factory to pass `buggy` to; a `remote` runtime drops every runtime kwarg, so a
  seeding requested against one is reported as not applied. A provenance marker that can be wrong is worse
  than none, so the connector stamps what happened, not what was asked for.
- **`engine/report.py`** — `to_junit` / `to_json` / `write_report` take `seeded` and emit
  `<property name="qensei.seeded" value="…"/>` and `"seeded": …`. Emitted on **every** report, `false`
  included: an absent marker would be ambiguous between "not seeded" and "written by a version that did not
  say".
- **`engine/run.py`** — announces a seeded run on stderr before the cases run *and* next to the verdict when
  something failed ("the failure above is SEEDED — this run proves detection works, not that the system
  regressed"), passes the real state to the report, and warns when `--seed-bug` had no effect.
- **`policies/communication-standards.md`** — the evidence rule this incident is an instance of: a
  gate-state claim carries the invocation that produced it, because this framework can produce either
  colour on demand. `docs/regression-gate.md` documents the new field.

**Not done, deliberately:** restricting the flag (option B in the issue). Seeding is a documented teaching
feature — `make demo`, `make diagnose-realbug`, the whole REAL_BUG walkthrough — and removing the capability
is a heavier call than labelling it. The stamp closes the harm at the artifact layer; if a manufacturable red
is later judged an integrity issue rather than an ergonomics one, B remains open on #41.

## Phase 3 — Tests

| Check | Command | Result |
|---|---|---|
| Engine + gate units | `make test-engine` | **161 passed** (was 150; +11 provenance pins) |
| Offline ritual | `make check` | OK |
| Full local CI | `make verify` | OK — ruff, pip-audit, pytest, fidelity, coverage-lint, panel records, secrets |
| The demo path still works | `make demo` | exit 0; `make diagnose-realbug` → REAL_BUG; `make diagnose-testbug` → TEST_BUG |
| Seeded gate, end to end | `engine.run --sut sut/mock-shop --seed-bug --report r.json` | exit 1, `SEEDED RUN … MANUFACTURED` on stderr, `"seeded": true`, `"failed": 1` |
| Healthy gate, end to end | same without the flag | exit 0, no banner, `"seeded": false` |
| Remote SUT | `--sut sut/widget-api --seed-bug` | `--seed-bug had NO EFFECT …`, not stamped seeded, exit 2 (the false-green guard on an unreachable SUT) |

The eleven pins cover the three places that can lie about provenance: the connector (did seeding apply?),
the report (does the artifact declare it?), and the gate end-to-end (does a real invocation stamp a real
artifact?). The last group runs the **real** gate against the **real** in-process SUT — the integration
boundary, not a mocked call.

## Phase 4 — Code quality

- The stamp is threaded from the one place that knows the truth (the connector) rather than from the CLI
  flag, which is what makes the remote case honest instead of merely documented.
- No new dependency; `engine/` stays stdlib. No case, pack or spec was touched, so no acceptance criterion
  moved.

## Phase 5 — Security

- `pip-audit`: no known vulnerabilities (dependencies unchanged). `make secrets`: clean.
- OWASP over the diff: no new input parsing, no subprocess, no deserialisation, no network. The new field is
  a boolean the gate computes about itself and writes into its own artifact.
- Supply-chain / agent-config: the CI `checks` job gains the new test module to its explicit list; no new
  action, no new dependency.

## Phase 5.5 — Release safety

- **Rollback:** revert the commit. The change is additive — one property in the JUnit, one field in the
  JSON, two stderr lines, one connector attribute. A consumer that ignores unknown fields is unaffected; the
  gate's pass/fail verdict and exit codes are unchanged (verified: seeded → 1, healthy → 0, unreachable → 2).

### Panel

- ran: this change IS a panel finding — `workflows/review-panel.js` surfaced it on the spec-005 PR-2 demonstrator run (decision ESCALATE, one framework-shape finding left for the human), and every claim in it was re-verified by hand before the issue was filed. Disposition: option A + C of the three the panel offered; B left open on #41.
- waived (Phase 4, this change's own cycle): no non-green gate result — the gate was green before and after; the seeded red used in testing is, by construction, the thing being labelled.

## Result

Offline checks green; CI to run on the PR. The gap #41 describes is closed at the artifact layer for every
SUT, with the demo path intact.
