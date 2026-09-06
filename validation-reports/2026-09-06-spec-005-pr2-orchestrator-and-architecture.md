# Validation Report — spec 005 PR 2: the deterministic orchestrator + the execution-architecture doc

**Date:** 2026-09-06
**Spec:** `specs/005-design-panel-and-invocation-tiers.md` — WS-D, WS-E and integration-boundary AC 3. With
these, all 20 acceptance criteria are met and the spec's Status moves to COMPLETE.
**Branch:** `feat/005-pr2-orchestrator-and-architecture`
**Scope:** the review-panel protocol as a Workflow-tool script driving the same lenses and the same
`engine/` gates, plus the timeline doc that says when each dispatch happens and who decides.

## What changed

- **`workflows/review-panel.js`** — ORIENT (`general-purpose`, read-only) → `engine.diagnostics`
  (mechanical, when a `pack` is given) → R-DIAGNOSIS (freshness self-gated) → R-EVIDENCE / R-MECHANISM
  (conditional on its flags, in parallel) → `engine.citation_gate` (mechanical, over the assembled
  findings) → JUDGE. Two `engine/` gates run as their own steps rather than as prose the JUDGE must
  remember. A **subject gate** throws on a string `args`, on a missing `sut`, and on a subject whose six
  fields are all empty. A `seed_bug` passthrough reproduces a regression with the framework's own
  `--seed-bug`; without it the mechanical step would re-run a healthy pack and report `NO_FAILURE`,
  contradicting the brief.
- **`workflows/README.md`** — the `args` contract, the return shape, and why the script coexists with the
  model-driven path (which stays the always-on default: the Workflow tool spawns several agents and runs
  only when a human asks).
- **`scripts/install.sh`** — symlinks `.claude/workflows -> ../workflows` alongside `commands` / `agents`,
  and the generated `.claude/CLAUDE.md` lists the orchestrator.
- **`docs/multiagent/execution-architecture.md`** — the three laws, the cast (`[BUILT]` / `[PROPOSED]`
  marked), the deterministic-gate table with exit codes, the `/automate` 0-5 timeline with its dispatches,
  the 15-row dispatch-conditions table, the lens-or-lint decision tree with the graduation path, the
  concurrency model, four worked examples from this repo, the anti-patterns and the cost model.
  `docs/multiagent/README.md` now says which of the three docs answers which question.

## The orchestrator ran end-to-end (integration-boundary AC 3)

Invoked via the Workflow tool with `{ sut: "sut/mock-shop", pack: "sut/mock-shop/packs/SHOP-456-discount",
seed_bug: true, failure: <the seeded REAL_BUG output>, env: <the local in-process env> }`.

**6 agents, 0 errors, all four phases** (Orient · Diagnose · Triage · Adjudicate), ~16 min wall clock.
The citation gate's raw output is echoed verbatim in the JUDGE digest as required — `18 citation(s) all
resolve`, `EXIT=0`, zero fabricated, zero unverifiable — alongside R-EVIDENCE's own run over 19 anchors
**with a negative control** (`app.py:9999` → `[FABRICATED] line 9999 out of range (file has 166)`;
`nonexistent.py:3` → `[FABRICATED] file does not exist`, exit 1), which is what proves the gate's exit 0
was not vacuous.

**Decision: `ESCALATE`** — and the reason is the finding.

### The panel refuted the premise of its own brief

The brief (written for this run) asserted "Regression gate red on sut/mock-shop". The panel verified that
claim instead of building on it: the gate is **green**, exit 0, `3 passed` — the red exists *only* under the
brief's own `seed_bug: true`. That is precisely the job of ORIENT's `contradicts_subject` and R-EVIDENCE's
"the green dot is not evidence" (here inverted: the *red* dot was not evidence either). The panel then
**declined to file a bug** and said so explicitly rather than silently, on three grounds it verified: the
"the platform regressed" wording is a verbatim f-string emitted for every `REAL_BUG`
(`engine/diagnostics.py:114-118`), not a finding about this system; the SUT source has exactly one commit,
so there is no regressing change; and a bug report for this rule already exists as a teaching fixture
(`sut/mock-shop/examples/reports/SHOP-456-bug.md`).

It also surfaced the disagreement it is designed to surface rather than resolving it: the deterministic lens
returned `REAL_BUG` (input-blind — it cannot see that the SUT was booted with a fault injected) while
R-DIAGNOSIS returned `ENV_OR_TRANSIENT`. Both were reported; neither overrode the other.

### The framework-shape gap it found (verified independently before recording)

`--seed-bug` is a flag on the **gate binary**, not only on the diagnostics entry point, and nothing marks a
seeded run in its output. Verified by hand this session:

| Claim | Verification |
|---|---|
| the gate accepts `--seed-bug` | `engine/run.py:46` (`add_argument`), `:57` (`sut.start(buggy=args.seed_bug)`) |
| nothing records the seeding | `grep -n 'seed\|buggy' engine/report.py engine/runner.py` → no match |
| the artifact is indistinguishable from a genuine red | `python3 -m engine.run --sut sut/mock-shop --seed-bug --report seeded.xml` → `2 passed, 1 failed`, **exit 1**; `grep -ci 'seed\|buggy' seeded.xml` → **0** |
| it is framework-wide, not a mock-shop concern | `--sut sut/restful-booker --seed-bug` → `[FAIL] BOOK-2 …`, exit 1 |
| the healthy gate is green | `python3 -m engine.run --sut sut/mock-shop` → exit 0 |

So a red, exit-1 gate run and its JUnit report can be produced on demand for any SUT with no provenance in
the artifact. The panel offered three dispositions (A: stamp provenance in the gate header and the report
schema; B: restrict the flag to an explicit demo context; C: document that a "gate red" claim must carry its
invocation line) and, correctly, decided none of them: this is a design call about the framework's own
integrity posture, and law 3 puts it with the human. **Left open for the human — deliberately not fixed in
this PR**, which is WS-D + WS-E. Recorded here so it is not lost.

That outcome is the demonstrator's real result: on its first genuine run the orchestrator caught a false
premise in the brief it was handed and produced a verified framework finding — the value the panel is
supposed to add, on a subject where a green-looking answer was the easy one.

## Phase 3 — Tests

| Check | Command | Result |
|---|---|---|
| Engine + gate units | `make test-engine` | 150 passed (unchanged — this PR adds no engine code) |
| Offline ritual | `make check` | OK — fidelity · coverage-lint · design-panel · panel-record · lint · secrets |
| Full local CI | `make verify` | OK |
| Script parses (raw and wrapped as the runtime evaluates it) | `node --check` | exit 0 both forms; `meta` is a pure literal |
| Every WS-D element present | 21 greps over the script + the `return` shape | all present |
| Orchestrator, live | Workflow tool, `scriptPath: workflows/review-panel.js` | 6 agents, 0 errors, 4 phases, decision `ESCALATE` |
| Wiring | `QENSEI_CLAUDE_WIRING=y ./scripts/install.sh` | `.claude/workflows -> ../workflows` created; the generated index lists it |
| Repo untouched by the run | `git status --short` before/after | only this PR's own files |

## Phase 4 — Code quality

- The script has no shell access by design, so both `engine/` gates run as single-purpose step-agents that
  report structured results — the citation gate is a step the JUDGE *receives*, not an instruction it must
  remember.
- Sequential-then-conditional dispatch is deliberate: R-DIAGNOSIS's flags decide whether the triage lenses
  run at all, so running them eagerly would spend two agents to save one agent's latency on a failure
  nobody has understood yet. The barrier before the JUDGE is real — it dedups across lenses.
- No engine or runtime code changed; no dependency added.

## Phase 5 — Security

- `pip-audit`: no known vulnerabilities (dependencies unchanged). `make secrets`: clean; the brief and the
  script carry no credentials.
- The script executes two commands, both repo-local `python3 -m engine.*` invocations with interpolated
  values that come from `args` — a caller-supplied `sut` / `pack` reaches a shell through the step-agent's
  prompt. Bounded, not eliminated: the Workflow tool is human-triggered per run, the agents are the same
  read-only lenses used elsewhere, and no value reaches a shell from an untrusted source. Worth stating
  rather than implying.
- Supply-chain / agent-config: a new `.claude/workflows` symlink into a versioned in-repo directory; no new
  dependency, no new action, no external fetch.

## Phase 5.5 — Release safety

- **Rollback:** revert the PR. Additive files (`workflows/`, one doc) plus the symlink line in
  `install.sh`; `rm -rf .claude/workflows` removes the wiring. The orchestrator is opt-in and human-
  triggered — nothing in `/automate`, the gate or CI depends on it.

### Panel

- ran: `workflows/review-panel.js` on SHOP-456 (the demonstrator itself) — ORIENT → engine.diagnostics (REAL_BUG) → R-DIAGNOSIS (ENV_OR_TRANSIENT, both surfaced) → R-MECHANISM → citation gate (18 anchors, exit 0, with a negative control) → JUDGE: **ESCALATE**, no bug filed, one verified framework-shape finding left for the human (seeded-red provenance).
- waived (Phase 4, this PR's own change): no non-green gate result — the change is a workflow script and docs; the regression gate was green throughout.

## Result

Offline checks green; CI to run on the PR. WS-D, WS-E and integration-boundary AC 3 are met, so **all 20
acceptance criteria of spec 005 are checked and its Status moves to COMPLETE**. One item is deliberately
left open for the human: the seeded-red provenance gap the orchestrator surfaced, which is a framework
design call, not part of this spec.
