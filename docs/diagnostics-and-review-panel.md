# Diagnostics & the review panel

When a case fails, the central question is: **TEST_BUG** (the test is wrong — fix it, never weaken the
spec) or **REAL_BUG** (the system regressed — keep the test red, file a bug)? Answering it requires
reading the backend **contract**, which is exactly why the framework has source access. Two layers
cooperate: a deterministic classifier (`engine/diagnostics.py`) and the advisory review panel
(`agents/`).

## The deterministic classifier (`engine/diagnostics.py`)

`diagnose(case_cls, sut)` runs the case, then walks a decision tree grounded in the backend's declared
`BUSINESS_RULES`:

```mermaid
flowchart TD
  d([diagnose: run the case]) --> ok{passed and no error?}
  ok -- yes --> NF[/NO_FAILURE/]
  ok -- no --> pre{precondition failed?<br/>_precondition_failed}
  pre -- yes --> PF[/PRECONDITION_FAILED<br/>a real verdict — adjudicate/]
  pre -- no --> err{raised an exception?}
  err -- yes --> ENV[/ENV_OR_TRANSIENT<br/>infra, not a contract verdict/]
  err -- no --> claim{contract_claim resolvable<br/>in BUSINESS_RULES?}
  claim -- no --> IND[/INDETERMINATE<br/>human adjudicates/]
  claim -- yes --> rate{claimed rate ==<br/>contract rate?}
  rate -- no --> TB[/TEST_BUG<br/>test asserts the wrong value —<br/>fix the test, do NOT weaken the spec/]
  rate -- yes --> RB[/REAL_BUG<br/>contract intact, runtime violated it —<br/>keep red, file a bug/]
```

The key distinctions:

- **PRECONDITION_FAILED vs ENV_OR_TRANSIENT** — a case that calls `expect.precondition(...)` raises
  `PreconditionError`, which the runner tags (`_precondition_failed`). Diagnostics treats that as a
  **real** verdict (the setup the contract depends on is absent), *not* a flake — so a genuine
  precondition failure is never dismissed as transient infra.
- **TEST_BUG vs REAL_BUG** — both require the case's `contract_claim` to resolve against a backend
  rule. If the claimed value disagrees with the source contract, the test is wrong (TEST_BUG); if it
  agrees but the running system violated it, the platform regressed (REAL_BUG). The spec intent is
  never weakened either way.

```bash
python3 -m engine.diagnose --sut sut/mock-shop --pack packs/SHOP-456-discount --seed-bug   # REAL_BUG
python3 -m engine.diagnose --sut sut/mock-shop --pack examples/diagnostics/SHOP-789-bad-test  # TEST_BUG
```

## The advisory review panel (`agents/`)

The classifier answers the mechanical question. The **review panel** adds judgement for the calls a
mechanism cannot make. It is advisory by construction: every lens carries `gate: false` and **none can
block a merge** — the human owns convergence; the panel *raises the floor*.

| Lens | Role | Deterministic counterpart it complements |
|------|------|------------------------------------------|
| **r-diagnosis** | classify TEST_BUG / REAL_BUG / TRANSIENT / escalate, before any fix | `engine/diagnostics.py` |
| **r-evidence** | anti-fabrication; verify each claim against raw source; the green dot is not evidence | `engine/citation_gate.py` |
| **r-mechanism** | force timing/scheduling/state reasoning into the open with `source:line` citations | `engine/freshness_gate.py` |
| **r-fidelity** | catch an edit that weakens an acceptance criterion to go green | `engine/fidelity_lint.py` |
| **r-uplift** | (migration only) verify a ported legacy test adopted framework patterns | — |
| **judge** | adjudicate the lenses' findings; write the escalation digest | — |

Each advisory lens has a **deterministic companion** that *can* gate (right column). The lens supplies
judgement (e.g. *is this restructured assertion a disguised weakening or a legitimate reshape?*); the
companion supplies the non-negotiable, identical-input-identical-verdict check. See
[quality-gates.md](quality-gates.md) for the companions and `agents/README.md` for the full registry.

## How they fit together on a failure

```mermaid
sequenceDiagram
  actor Human
  participant Gate as engine.run (gate)
  participant Diag as engine.diagnostics
  participant Panel as review panel (agents/)
  participant Gates as deterministic gates
  participant Judge as judge

  Gate-->>Human: a case is RED
  Human->>Diag: diagnose(case, sut)
  Diag->>Diag: read BUSINESS_RULES contract
  Diag-->>Human: verdict (REAL_BUG / TEST_BUG / PRECONDITION_FAILED / …)
  Human->>Panel: run the lenses on the failing/changed test
  Panel->>Gates: fidelity_lint / citation_gate / freshness_gate
  Gates-->>Panel: deterministic findings (block-class)
  Panel->>Panel: r-diagnosis / r-evidence / r-mechanism / r-fidelity (judgement)
  Panel->>Judge: findings
  Judge-->>Human: escalation digest (BLOCK / FIX / FLAG / ESCALATE)
  Note over Human: the human decides — the panel never blocks the merge
```

The discipline that binds both layers: **the validation objective stated in the spec is never weakened
to make a test pass.** If the backend legitimately cannot satisfy an acceptance criterion, the test is
correctly red and the bug is real.

See also: [the regression gate](regression-gate.md), [deterministic quality gates](quality-gates.md).
