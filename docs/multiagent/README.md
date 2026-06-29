# Review panel

An advisory, read-only multi-agent panel that **diagnoses and verifies a failing or
changed test** — inside the `/spec-test` validate-and-iterate loop (Phase 4) or on-demand
when a human points it at a failed regression-gate / CI run.

The panel is **advisory and never gates the merge.** The deterministic regression gate
(`engine/run.py` / `make test`, green on every configured environment) remains the source
of truth for "green". The panel raises the floor — surfacing weakenings, fabricated
evidence, and uncited mechanism claims before a human acts on them — while the human owns
convergence. No verdict, rebuttal, or digest may weaken an approved acceptance criterion to
make a test pass.

It is **read-only**: lenses read the change, the spec, the knowledge stores, and the System
Under Test (SUT) source through the active plugin's `SUTConnector` (`engine/sut.py`). They
write no repo files (only their own memory), file no tickets, and trigger no live runs.

## Read next

- **[`review-panel.md`](./review-panel.md)** — the protocol: the orchestration sequence,
  entry points, the rebuttal / loop-budget rules, and the escalation digest contract.
- **[`../../agents/`](../../agents/)** — the lens definitions (one Markdown agent file each).

## The lenses

| Lens | File | Role | Verdicts |
|------|------|------|----------|
| **JUDGE** | [`agents/judge.md`](../../agents/judge.md) | Adjudicates the lenses' findings, dedups, runs the rebuttal protocol, writes the decision-grade escalation digest. | `BLOCK` / `FIX` / `FLAG` / `ESCALATE` per finding |
| **R-DIAGNOSIS** | [`agents/r-diagnosis.md`](../../agents/r-diagnosis.md) | Diagnoses the failure **before any fix** — is it the test or the system? Judgment-side complement to `engine/diagnostics.py`. | `TEST_BUG` / `REAL_BUG` / `TRANSIENT` / `UNDOCUMENTED-ESCALATE` |
| **R-EVIDENCE** | [`agents/r-evidence.md`](../../agents/r-evidence.md) | Skeptic / anti-fabrication: pulls raw gate state (the green dot is not evidence), resolves every source citation, checks cross-test / durable / env-divergence impact. | `SUPPORTED` / `UNSUPPORTED` / `CONTRADICTED` |
| **R-MECHANISM** | [`agents/r-mechanism.md`](../../agents/r-mechanism.md) | Forces SUT-mechanism reasoning (timing / SLA / scheduling / run-eligibility / coalescing / component state) into the open, anchored to exact SUT-source lines. | `CITED` / `UNCITED` / `MISREAD` |
| **R-FIDELITY** | [`agents/r-fidelity.md`](../../agents/r-fidelity.md) | Spec-fidelity check on every test edit: did the change loosen an assertion to turn red green? Advisory companion to the deterministic fidelity lint. | `WEAKENING-DETECTED` / `RESHAPE-ESCALATE` |
| **R-UPLIFT** | [`agents/r-uplift.md`](../../agents/r-uplift.md) | Migration-only — verifies a port from a legacy repo adopted this framework's patterns without losing the behavioural contract. **Not part of the failure-triage panel.** | `UPLIFTED` / `ANTIPATTERN-IMPORTED` / `BEHAVIOR-LOST` |

## Relationship to the deterministic engine

The panel sits **alongside**, not above, the deterministic code lens
[`engine/diagnostics.py`](../../engine/diagnostics.py). That lens classifies a failure
mechanically: it reads the SUT contract (`BUSINESS_RULES`, via the `SUTConnector` source)
and compares the case's `contract_claim` to the runtime response —

- claim disagrees with the contract → `TEST_BUG` (fix the test; never weaken the spec);
- claim agrees but the running system violated it → `REAL_BUG` (keep the test red, file a bug);
- the case threw → `ENV_OR_TRANSIENT`; no resolvable claim → `INDETERMINATE`.

Because it has no judgement, it can hard-gate as a lint. The advisory lenses **complement**
it for the calls the heuristic cannot make — an `INDETERMINATE` case, an undocumented flow,
a serial-pass / parallel-fail execution gap, or a reshaped-vs-weakened assertion. When the
deterministic verdict and an advisory lens disagree, the JUDGE surfaces both: the
deterministic verdict is evidence, not an override.
