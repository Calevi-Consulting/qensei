# Review-panel protocol

The single source of truth for **how the multi-agent lenses run together** on a failing or changed test.
Referenced by `/spec-test` Phase 4 (the automatic gate — the validate-and-iterate loop) and by the
**on-demand** path (a human points the agent at a failed regression-gate / CI run). It is **not** a
context-free trigger — the panel runs only when there is a concrete failure/change to review (the
`review-panel` skill is the model-driven invocation, and always takes one failing/changed test as its
argument).

The panel is **domain-agnostic**: it reviews tests for whatever product is wired in as a plugin under
`sut/<name>/`. Everything a lens reads about the System Under Test's behaviour is reached through that
plugin's **SUTConnector** (`engine/sut.py` → `source_module()` / `source_path()`), never a hard-coded
backend.

## The lenses

Six lenses, all read-only and advisory (`agents/`):

- **JUDGE** — adjudicates the findings, runs the rebuttal protocol, writes the escalation digest.
- **R-DIAGNOSIS** — diagnoses the failure BEFORE any fix (`TEST_BUG` / `REAL_BUG` / `TRANSIENT` /
  `UNDOCUMENTED-ESCALATE`); the judgment-side complement to the deterministic `engine/diagnostics.py`.
- **R-EVIDENCE** — anti-fabrication, raw gate/run-state verification, cross-test / durable / env-divergence.
- **R-MECHANISM** — verifies SUT-mechanism reasoning (timing / scheduling / run-eligibility / coalescing /
  component-and-deployment state) against the SUT source, and surfaces every mechanism call.
- **R-FIDELITY** — the spec-fidelity lint: blocks a weakened acceptance criterion, escalates a reshape.
- **R-UPLIFT** — **migration-only**; verifies a legacy test ported into this framework adopted its patterns
  without dropping the behavioural contract. **Not part of the failure-triage sequence below** — it runs
  only in the legacy→framework migration variant, never in greenfield spec authoring or Phase-4 triage.

There is **also a deterministic code lens**, `engine/diagnostics.py`, that classifies a failure
`REAL_BUG` vs `TEST_BUG` mechanically — it compares a case's `contract_claim` to the SUT's declared
contract (`BUSINESS_RULES`, read via the SUTConnector source) and the runtime response. The advisory
**R-DIAGNOSIS** lens *complements* it for the judgment calls the heuristic cannot make (`INDETERMINATE`
cases, undocumented flows, serial-pass / parallel-fail execution-flow gaps). Same vocabulary, added
judgement. When the two disagree, surface both — the deterministic verdict is evidence, not an override.

## Two implementations (coexist)

This doc is the **spec**; there are two ways to run it, sharing the same lenses (orchestrator-agnostic):
- **Model-driven** — the driving agent (or the `review-panel` skill) *follows* this protocol, invoking
  the `agents/` lenses as subagents. Default for the lightweight auto path; native to `/spec-test`
  Phase 4 inline.
- **Deterministic** — the mechanical parts run as code/lints at the point of consumption:
  `engine/diagnostics.py` (the `REAL_BUG` / `TEST_BUG` contract check), the **SUT-source freshness
  check**, and the **citation resolution check**. An orchestrator can sequence the advisory lenses around
  those for structured findings, live observability, and scale (the future streaming/dedup layer calls
  the panel once per deduped root cause).

The **only** difference between the two paths is *who drives the fan-out* — the agent following the
protocol via subagents, vs a script sequencing the lenses deterministically. Everything below — the
lenses, the conditional skip, the freshness self-gate, the verdicts, the outcomes — is identical.

## Two entry points, one protocol
- **Automatic** — `/spec-test` Phase 4, on each non-green result of the regression gate.
- **On-demand** — a human gives the agent a specific failure (a regression-gate run, a CI job, a test) to
  analyse and fix. Same fix→test→fix loop, so the same protocol applies. (R-FIDELITY's pre-commit lint and
  R-DIAGNOSIS's on-demand trigger already work here regardless of `/spec-test`.)

## Flow (both orchestrators)

```
                          A FAILURE / CHANGE TO REVIEW
            (/spec-test Phase 4 | on-demand inline | streaming layer)
                                        │
                  ┌─────────────────────┴─────────────────────┐
                  ▼                                           ▼
  ┌─ MODEL-DRIVEN ────────────────┐         ┌─ DETERMINISTIC ─────────────────┐
  │ driving agent / review-panel  │         │ an orchestrator drives the      │
  │ skill FOLLOWS this doc, via    │         │ lenses; the mechanical checks   │
  │ subagents (agents/)            │         │ run as code/lints               │
  │ adaptive, task-panel           │         │ deterministic, structured       │
  └───────────────┬───────────────┘         └─────────────────┬───────────────┘
                  └─────────────────────┬─────────────────────┘
                                        ▼     SAME lenses, SAME sequence
             ┌──────────────────────────────────────────────────────┐
             │ 1. R-DIAGNOSIS  (always, first)                      │
             │ SUT-source freshness self-gate -> stale? -> ESCALATE │
             │ -> verdict + needs_evidence / needs_mechanism        │
             └──────────────────────────┬───────────────────────────┘
                   branch on R-DIAGNOSIS's flags (skip what isn't needed)
                ┌───────────────────────┴───────────────────────┐
                ▼ needs_evidence               needs_mechanism  ▼   (parallel)
      ┌──────────────────┐                            ┌──────────────────┐
      │ 2. R-EVIDENCE    │                            │ 2. R-MECHANISM   │
      │ raw state,       │                            │ SUT-source-cited │
      │ anti-fab,        │                            │ mechanism,       │
      │ cross-test       │                            │ surfaced         │
      └─────────┬────────┘                            └─────────┬────────┘
                └───────────────────────┬───────────────────────┘
                                        ▼
             ┌──────────────────────────────────────────────────────┐
             │ 2.5 CITATION GATE (deterministic, over the findings) │
             │ resolve every sut/<name>/source/<path>:<line>        │
             │  fabricated (MISSING-FILE/OOR) -> drop the claim     │
             │  unverifiable (MISSING-SOURCE) -> fetch / escalate   │
             └──────────────────────────┬───────────────────────────┘
                                        ▼
             ┌──────────────────────────────────────────────────────┐
             │ 3. JUDGE -> BLOCK / FIX / FLAG / ESCALATE            │
             │ dedup, rebuttal (2x same -> STOP), no auto-merge     │
             └──────────────────────────┬───────────────────────────┘
         ┌──────────────────────────────┼─────────────────────────────┐
         ▼                              ▼                             ▼
      4. FIX with context       REAL_BUG ->                  unresolved ->
      -> R-FIDELITY lint        structured report ->         escalation digest ->
      (pre-commit) -> re-run    ticket provider (human)      HUMAN decides
```

## The sequence (on a failure)

0. **SUT-source freshness gate (blocking).** Confirm the SUT source the lenses will read is fresh FIRST.
   The freshness depends on the active plugin's `runtime.mode` in `manifest.json`:
   - **`in_process`** (the in-repo mock): the source ships in this repo and *is* the running app, so it is
     **always fresh** — the check is a no-op; proceed.
   - **`remote`** (a real backend): the source is a checked-out clone — run the plugin's clone-freshness
     check (local HEAD == origin default). If it reports STALE/DIRTY, **STOP** and refresh before any lens
     reads or cites `sut/<name>/source/...`.

   R-DIAGNOSIS and R-MECHANISM also self-gate on this (they run the check themselves), so a stale clone
   cannot be silently consumed — the enforcement is at the **point of consumption**, not "remember to
   check".

1. **① R-DIAGNOSIS — diagnose BEFORE any fix.** Reads the case + fixtures + both knowledge stores
   (`policies/` framework-shape, `sut/<name>/learnings/` + `sut/<name>/skills/` domain/system-shape) + the
   spec (`core/specs/<id>.md`) + the SUT source via the SUTConnector. When the case carries a resolvable
   `contract_claim`, run `engine/diagnostics.py` first and echo its verdict; R-DIAGNOSIS exists for the
   calls the heuristic cannot make. Verdict `TEST_BUG` / `REAL_BUG` / `TRANSIENT` / `UNDOCUMENTED-ESCALATE`,
   cited. Sets `needs_evidence` / `needs_mechanism` flags for the next step.

2. **② Triage lenses (as relevant).** R-EVIDENCE (raw gate/run state, anti-fabrication, cross-test /
   durable-collision / env-divergence) and, when the failure turns on timing/scheduling/run-eligibility/
   SUT-component behaviour, R-MECHANISM (SUT-source-cited mechanism, surfaced). Branch on R-DIAGNOSIS's
   flags — skip the lens that isn't needed.

2.5. **②′ Citation gate (deterministic, blocking on fabrication).** Run the **citation resolution check**
   over the assembled lens findings BEFORE the JUDGE adjudicates — a forcing function at the point of
   consumption, not "the JUDGE remembers". A deterministic orchestrator runs it as a dedicated step between
   the lenses and the JUDGE; the model-driven path runs it in the JUDGE step. For the in-repo mock every
   `sut/<name>/source/<path>:<line>` is directly checkable with Read/Grep; a `remote` plugin may ship a
   citation tool. A **MISSING-FILE / LINE-OUT-OF-RANGE** (path/line absent from a PRESENT source) is
   **fabrication** → the claim does not clear. A **MISSING-SOURCE** (the SUT source is not fetched — e.g. a
   remote backend's clone is absent) is **unverifiable here, not fabrication** → fetch the source and
   re-cite, or escalate as a labelled hypothesis.

3. **③ JUDGE adjudicates.** Dedup/rank the findings; decide `BLOCK` / `FIX` / `FLAG` / `ESCALATE` per
   finding; run the rebuttal protocol (2× the same finding + same class of rebuttal → STOP); on `REAL_BUG`
   assemble a structured report and route it to the human to file via the **ticket provider** (the
   `ticket/` abstraction — the JUDGE never opens the ticket itself); surface every SUT-mechanism call.
   **Echo the citation gate's output as proof it ran** (do not merely assert it did).

4. **④ Fix WITH context → R-FIDELITY → re-run.** The generator fixes using the diagnosis, never weakening
   the spec. **R-FIDELITY** (the pre-commit lint) blocks a weakened criterion and escalates a reshape on
   commit, regardless of entry point (acknowledge a confirmed reshape with `--allow-reshape`). Re-run the
   regression gate.

- **genuine regression / infrastructure → STOP** (the test is correctly red); a `REAL_BUG` → ticket
  provider (human-gated).
- **unresolved escalation → decision-grade escalation digest → human.**

## Invariants

- The loop **never weakens an acceptance criterion** in `core/specs/` to make a test pass. If the SUT
  legitimately cannot satisfy a criterion, the test is correctly red and the bug is real.
- The lenses are **advisory** and never gate the merge. The **regression gate** — `engine/run.py` /
  `make test`, green on every **configured environment** (the entries in the active plugin's
  `manifest.json` `env`), plus CI — is the truth for "green". The panel raises the floor; **the human owns
  convergence.**
- **Route every claim to the SUT SOURCE via the SUTConnector for the active `sut/<name>/` plugin.** Every
  claim about the SUT's behaviour is verified against the source the connector exposes
  (`engine/sut.py` → `source_module()` / `source_path()`, i.e. `sut/<name>/source/`) — not from priors, not
  from a test mock/fixture, not from memory, not from the wrong source layer. A claim from any of those is
  **UNCITED** and does not clear. The routing by claim class:

  | Claim is about… | Routed to / verified as |
  |---|---|
  | the SUT's internal **mechanism** — when/whether an operation fires · run-eligibility · scheduling / SLA-window math · run-coalescing · component/service state | the SUT SOURCE via the SUTConnector → **R-MECHANISM** (cite `sut/<name>/source/<file>:<line>`) |
  | what a downstream **component emits** · its config / source types · query construction · auth | the SUT SOURCE for *that* component (the plugin's own source layout) → the owning lens |
  | a **UI route** / in-app URL · selector or test-id · FE-side validation · visible copy (only when the SUT exposes a UI) | the SUT SOURCE's UI contract → **R-DIAGNOSIS** — a drift here is a `TEST_BUG`, **lowest-cost**, and does **not** set `needs_mechanism` |
  | which components **exist / should exist** · the deployment model · a concurrency limiter (**topology**) | the SUT SOURCE deployment/topology layer (a separate source tree / manifest / domain skill — NOT the request path, NEVER a mock) → **R-MECHANISM**, **highest-cost** |
  | is this a `REAL_BUG` or a `TEST_BUG` | the deterministic **`engine/diagnostics.py`** (`contract_claim` vs `BUSINESS_RULES` vs runtime) + **R-DIAGNOSIS** for the judgment calls the heuristic cannot make |

  **The citation must RESOLVE, not just name a source.** Freshness proves the source is current; it does
  not prove a cited `file:line` exists. The citation resolution check runs over the findings after the
  lenses and before the JUDGE adjudicates. It separates two "not found" cases: a **MISSING-FILE /
  LINE-OUT-OF-RANGE** (path/line absent from a PRESENT source) is **fabrication** and the claim does not
  clear; a **MISSING-SOURCE** (the owning source not fetched) is **unverifiable here, not fabrication** —
  fetch it or escalate the claim as a labelled hypothesis. A claim with **no `file:line` at all** (a
  runtime/log/REST fact, or a mechanism only a backend developer can confirm) emits no citation, so the
  check is silent and the UNCITED rule governs it. This closes the exact hole where a fabricated path can
  pass the freshness check yet point at nothing — without falsely condemning legitimate claims that simply
  lack a checkable source.

- **SUT topology / deployment model is the highest-cost claim.** Any claim that *which components exist /
  should exist* (a component is "missing", a service is "degraded", a named component "drives" the work) is
  verified against the SUT SOURCE's deployment/topology layer for the active plugin — NOT the request path
  and NEVER a test mock (a mock lists what is *possible*, not what is *deployed*) — and only after the
  deployment model is confirmed. R-DIAGNOSIS marks any such claim it has not so confirmed as `hypothesis:`
  + `needs_mechanism`; R-MECHANISM verifies it there or returns `UNCITED`. **A UI route/selector/copy claim
  is the lowest-cost** — it is *not* mechanism: it is sourced from the SUT source's UI contract by
  R-DIAGNOSIS, is a `TEST_BUG` when it drifts, and does NOT set `needs_mechanism`. (A UI test that fails
  because a *backend API it calls* misbehaves is a mechanism claim, routed to R-MECHANISM on its merits.)

- **The routing + freshness discipline applies to BOTH entry points, on-demand included.** This invariant
  is not scoped to `/spec-test`. Whenever a lens runs — automatic (Phase 4) or on-demand (a human points
  the agent at a failed regression-gate / CI run) — every claim is routed to the SUT source via the
  SUTConnector (table above) and the fresh source is the only acceptable origin. The freshness check is a
  forcing function at the **point of consumption**, so it fires regardless of which entry point invoked the
  lens. The classic failure mode — the on-demand path consuming a stale/absent clone because the freshness
  check only fired inside `/spec-test` — is closed here: the lens self-gates wherever it runs.

- **A "degraded / missing-component" verdict needs a positive "expected-here" citation.** The JUDGE does
  not accept argument-from-absence without a source-of-truth line that the component is expected in this
  deployment. **Cross-lens consensus is not verification** — a premise every lens shares still goes through
  the rebuttal pass; verify the node (the component is genuinely absent and was expected), not only the
  causal arrow (the absence causes the failure).

- **Personas govern data-durability claims.** `new_user` (ephemeral, self-cleaning) and `existing_data`
  (durable, find-or-create on a stably-named long-lived object) are defined in `policies/`. R-EVIDENCE uses
  them to judge intentional sharing vs collision on durable objects; a durable that another pack relies on
  is not a collision when it is shared on purpose.

See the per-lens docs in `agents/` (`judge`, `r-diagnosis`, `r-evidence`, `r-mechanism`, `r-fidelity`,
`r-uplift`) for each lens's full contract, and `docs/overview.md` for the architecture and lineage.
