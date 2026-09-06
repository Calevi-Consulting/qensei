# Execution architecture — when a subagent runs

The **timeline** view of the multi-agent strategy. The other two docs answer different questions:

| Doc | Question it answers |
|---|---|
| [review-panel.md](review-panel.md) | *How* the lenses run together on ONE failing/changed case (the protocol) |
| [r-design.md](r-design.md) | What the design-stage lens checks, and why it reports into an existing human gate |
| **this doc** | **At what moment of the main agent's work does a subagent appear, under what condition, and who decides?** |

Read this one first if you are asking "should I spawn something here?".

## Status legend

Everything below is marked, because a doc that blurs built-from-planned is worse than no doc.

- **`[BUILT]`** — exists, wired, running today.
- **`[PROPOSED]`** — designed, not implemented. Do not cite as behaviour.

## The three laws

Every dispatch decision in this repo reduces to these.

**1. The main agent owns the timeline.** Subagents are *called and return*; they never drive the phase
sequence, never commit, never merge, never file a ticket. The main agent (the GENERATOR) holds the full
context and is the only actor that writes code. A subagent that "took over" is a bug.

**2. Deterministic-first — never LLM what a rule can decide.** A model inside a mechanical check imports
non-determinism (block Monday, pass Tuesday on identical input — fatal for a regression suite), cost, and a
false "VERIFIED" stamp. `engine/` is stdlib and runs with **no AI in the loop**; it is the single source of
truth for green. The corollary is the **graduation path**: when a lens finding recurs, it stops being a
lens finding and becomes a lint. Precedent in this repo — R-COVERAGE's mechanical half became
`engine/coverage_lint.py` (does the declared metadata *resolve*?) while its semantic half (does `run()`
actually *exercise* the criterion?) stayed with the lens.

**3. Advisory, with a deterministic record.** Lenses never gate the merge — the regression gate
(`engine/run.py`, green on every configured environment) is the only truth for green, and the human owns
convergence. But *whether a panel ran* is recorded and linted (`engine/design_panel_lint.py`,
`engine/panel_section_lint.py`), because a policy without a gate is not followed. Those lints gate
**presence, not verdict**: `REJECTED` passes exactly like `APPLIED`, and a documented waiver passes.

## The cast

| Actor | Type | `agentType` | Authority | Status |
|---|---|---|---|---|
| GENERATOR | main agent | — | writes everything | `[BUILT]` |
| R-DESIGN | LLM, read-only | `r-design` | review the (spec, plan) pair before code; sets flags | `[BUILT]` |
| R-DIAGNOSIS | LLM, read-only | `r-diagnosis` | diagnose before fixing; sets flags | `[BUILT]` |
| R-EVIDENCE | LLM, read-only | `r-evidence` | raw gate state, anti-fabrication, cross-test | `[BUILT]` |
| R-MECHANISM | LLM, read-only | `r-mechanism` | SUT-source-cited mechanism claims | `[BUILT]` |
| R-COVERAGE | LLM, read-only | `r-coverage` | does the pack exercise every AC; metadata vs source | `[BUILT]` |
| R-FIDELITY | LLM, read-only | `r-fidelity` | weakening-vs-baseline judgement (its lint is the gate) | `[BUILT]` |
| R-UPLIFT | LLM, read-only | `r-uplift` | legacy-port review (migration only) | `[BUILT]` |
| JUDGE | LLM, read-only | `judge` | dedup, adjudicate, escalation digest | `[BUILT]` |
| ORIENT | LLM, read-only | `general-purpose` | assemble the record — **no verdict, not a lens** | `[BUILT]` |

Deterministic gates, by the moment they fire:

| Gate | Fires at | Blocks on | Exit |
|---|---|---|---|
| `engine/run.py` false-green guard | every gate run | no cases discovered / all skipped / SUT unreachable / creds unresolved | `2` |
| `engine/freshness_gate.py` | before any SUT-source read; self-gated inside R-DIAGNOSIS, R-MECHANISM, R-DESIGN | a stale/dirty remote source clone | `1` |
| `engine/fidelity_lint.py` | every pack edit + pre-commit + CI | a weakened acceptance criterion vs the git baseline | `1` |
| `engine/coverage_lint.py` | every pack (no baseline needed) + pre-commit + CI | `covers` / `contract_claim` / `spec_ref` inconsistent or unresolvable | `1` / `2` if no packs found |
| `engine/citation_gate.py` | between the lenses and the JUDGE | a `file:line` a lens cited that does not resolve | `1` fabricated / `3` unverifiable |
| `engine/design_panel_lint.py` | pre-commit + `make check` + CI, on changed plans | a touched plan with no `## Design panel` record, or a declared count without matching `F<n>` dispositions | `1` / `2` if git cannot list changes |
| `engine/panel_section_lint.py` | pre-commit + `make check` + CI, on changed reports | a touched validation report with no `### Panel` `ran:`/`waived:` line | `1` / `2` if git cannot list changes |
| `engine/diagnostics.py` | on a failure, before any lens reasons | — (it classifies, it does not block) | verdict |

## The master timeline

The spine is the main agent running `/automate`. Branches to the right are dispatches; everything returns
to the spine.

```
  MAIN AGENT (GENERATOR)                    DISPATCHED WORK
  ══════════════════════                    ═══════════════
          │
   ┌──────▼───────────────────┐
   │ PHASE 0 · ORIENT         │
   │ README · overview        │──► make freshness ──► [freshness_gate]  BLOCKING
   │ policies/ · SUT skills   │◄── ✓ fresh · ✗ STALE → STOP, sync-source ┘
   │ SUT learnings            │      (no-op for in_process and sourceless SUTs)
   └──────┬───────────────────┘   no subagent — the main agent must hold this context
          │
   ┌──────▼───────────────────┐
   │ PHASE 1 · GATHER         │
   │ ticket via ticket/       │   no lens. `make design` (engine/design.py) seeds
   │ provider + comments      │   candidate coverage — a deterministic report, not an agent.
   │ ASK persona coverage ◄───┼── HUMAN GATE: persona choice ──
   └──────┬───────────────────┘
          │
   ┌──────▼───────────────────┐
   │ PHASE 2 · SPEC           │
   │ intent only: context,    │
   │ AC, persona, risks       │   ── HUMAN GATE: spec approval ──
   └──────┬───────────────────┘   ◄── the design panel reports HERE, into an
          │                           existing gate; it does not add a new one
   ┌──────▼───────────────────┐
   │ PHASE 2b · PLAN          │
   │ REST mapping · case      │──► [coverage_lint]  (where a pack exists)  deterministic first
   │ shape · persona · budget │──► R-DESIGN        (Tier 1, always)
   │                          │──► R-MECHANISM / R-EVIDENCE  (Tier 2, flagged)
   │                          │◄── findings ──────── record: [design_panel_lint]
   └──────┬───────────────────┘
          │
   ┌──────▼───────────────────┐
   │ PHASE 3 · IMPLEMENT      │
   │ make new-pack / new-ui-  │──► [fidelity_lint]  on every case edit
   │ pack, then fill it in    │──► [coverage_lint]  covers ↔ README ↔ source
   └──────┬───────────────────┘
          │
  ╔═══════▼═══════════════════════════════════════════════════════════════════╗
  ║ PHASE 4 · VALIDATE-AND-ITERATE       cap: 3 cycles per ROOT CAUSE          ║
  ║                                                                           ║
  ║   4a  make test / CI across every configured env (manifest `env`)         ║
  ║                    ▼                                                      ║
  ║            ┌───────────────┐  green, no pack regressed                    ║
  ║            │ gate green ?  │ ─────────────────────────────► PHASE 5       ║
  ║            └───────┬───────┘   (exit 2 = false-green guard = NOT green)   ║
  ║                    │ NON-GREEN                                            ║
  ║   4b  ┌────────────▼─────────────────────────────────────────────┐        ║
  ║       │ TIER 1 — ALWAYS, NON-DISCRETIONARY                       │        ║
  ║       │ ORIENT (record) → engine/diagnostics.py (if a claim      │        ║
  ║       │ resolves) → R-DIAGNOSIS as a SUBAGENT, before any fix    │        ║
  ║       │ inline self-triage is NOT a substitute                   │        ║
  ║       │ → verdict + needs_evidence / needs_mechanism             │        ║
  ║       └────────────┬─────────────────────────────────────────────┘        ║
  ║                    │ any Tier-2 trigger?                                  ║
  ║          ┌─────────┴──────────┐                                           ║
  ║       no │                    │ yes                                       ║
  ║          │      ┌─────────────▼──────────────┐                            ║
  ║          │      │ TIER 2 — FULL PANEL        │                            ║
  ║          │      │  R-EVIDENCE ∥ R-MECHANISM  │ parallel, flag-gated       ║
  ║          │      │        ▼                   │                            ║
  ║          │      │  [citation_gate]  BLOCKING │ fabricated → claim dropped ║
  ║          │      │        ▼                   │                            ║
  ║          │      │  JUDGE → BLOCK/FIX/        │                            ║
  ║          │      │          FLAG/ESCALATE     │                            ║
  ║          │      └─────────────┬──────────────┘                            ║
  ║          └─────────┬──────────┘                                           ║
  ║                    ▼                                                      ║
  ║   4c  fix WITH context ──► [fidelity_lint] + R-COVERAGE ──► re-run ──┐    ║
  ║       + capture a learning every cycle                               │    ║
  ║   4d  3 cycles same root cause → STOP, escalate ◄────────────────────┘    ║
  ║   4e  exit: green everywhere AND every R-COVERAGE GAP resolved/accepted   ║
  ╚═══════════════════════════════════════════════════════════════════════════╝
          │
   ┌──────▼───────────────────┐
   │ PHASE 5 · RECORD         │
   │ validation report        │──► [panel_section_lint]   ran | waived
   │ spec reconciliation      │──► the spec lands in the same change
   │ pack README index card   │──► make regen-index
   │ learnings                │
   └──────────────────────────┘
          │
          ▼  ── HUMAN GATE: PR review + merge ──
```

Two dispatches live **outside** this timeline: **R-UPLIFT** (only when porting a test from a legacy repo)
and **R-COVERAGE** run on-demand against a landed pack.

## Dispatch conditions

The single table to consult before spawning anything.

| # | Dispatch | Condition (exact) | Tier | Returns |
|---|---|---|---|---|
| 1 | `freshness_gate` | before ANY read of a SUT's source, at every entry point | blocking | ✓ / STALE |
| 2 | `coverage_lint` | Phase 2b (where a pack exists) and every pack edit | blocking | consistent / BLOCK |
| 3 | **R-DESIGN** | **every new pack at Phase 2b**, after the plan is drafted, before implementing | 1, always | ≤6 findings `F1..Fn` + flags |
| 4 | R-MECHANISM @2b | R-DESIGN set `needs_mechanism` | 2 | CITED / UNCITED / MISREAD |
| 5 | R-EVIDENCE @2b | R-DESIGN set `needs_evidence` | 2 | SUPPORTED / UNSUPPORTED / CONTRADICTED |
| 6 | **HUMAN @2b** — there is deliberately **no JUDGE here** | always, on R-DESIGN findings | — | which findings are taken |
| 7 | ORIENT | every non-green gate result, before any lens reasons | 1, always | the record (no verdict) |
| 8 | `engine/diagnostics.py` | a failing case carrying a resolvable `contract_claim` | 1, always | REAL_BUG / TEST_BUG / … |
| 9 | **R-DIAGNOSIS** | **every** non-green gate result, before any code change | 1, always | verdict + flags |
| 10 | R-EVIDENCE | R-DIAGNOSIS set `needs_evidence` | 2 | raw state, cross-test impact |
| 11 | R-MECHANISM | R-DIAGNOSIS set `needs_mechanism` | 2 | SUT-source-cited mechanism |
| 12 | `citation_gate` | after the lenses, before the JUDGE — always, when lenses ran | blocking | resolves / fabricated |
| 13 | JUDGE | any Tier-2 trigger fired | 2 | BLOCK/FIX/FLAG/ESCALATE + digest |
| 14 | R-COVERAGE | every new or changed pack — **even when the gate is green** | ritual | COVERED / GAP / CLAIM-MISMATCH |
| 15 | R-UPLIFT | porting a test from a legacy repo | migration | UPLIFTED / ANTIPATTERN / BEHAVIOR-LOST |

**Tier-2 triggers in Phase 4** — ANY one is sufficient:

```
   needs_evidence OR needs_mechanism flagged
   OR verdict ∈ { REAL_BUG, UNDOCUMENTED-ESCALATE }
   OR this is the 2nd cycle on the SAME root cause
   OR the fix needs an R-FIDELITY reshape ack (--allow-reshape)
   OR the branch lands a NEW PACK (its first landing)
```

That last trigger is the non-obvious one, and it is the one that pays. A green gate on a new pack proves
the pack passes; it does not prove it is the right pack — `coverage_lint` checks that the metadata
*resolves*, not that it is *right*, and only a reader asks whether `covers` names what the case actually
exercises.

**Who adjudicates Phase-2b findings.** The **human**, at the spec-approval gate that already exists. The
GENERATOR writes a *proposed* disposition per finding into the plan
(`- F<n> APPLIED|REJECTED|FLAGGED|DEFERRED: <reason>`, gated for presence and count by
`design_panel_lint.py`); the human ratifies or overrides. No agent decides which findings are taken.

The asymmetry with row 13 is the point, not an omission. Phase 4 needs a JUDGE **because it has no human
in the loop**: the validate-and-iterate cycle can run three times, generating and applying fixes, with
nobody looking. Phase 2b already stops at a human one step later and fields one or two lenses with at most
six findings — no dedup, no rebuttal protocol, nothing for a judge to do that the approval gate does not.
Adding one would put an adjudicator in front of an adjudicator and make an advisory lens the de-facto
design gate — against law 3. Revisit only if 2b grows to three or more lenses with overlapping findings.

## Lens or lint?

The decision that keeps the architecture from bloating.

```
                    a check you want to add
                              │
                    ┌─────────▼──────────┐
                    │ Same input always  │
                    │ ⇒ same verdict?    │
                    └─────────┬──────────┘
                    yes       │        no
              ┌───────────────┘        └────────────────┐
              ▼                                         ▼
   ┌────────────────────┐                  ┌────────────────────────┐
   │ Is the input       │                  │ Does it need judgement │
   │ machine-readable   │                  │ ACROSS artifacts       │
   │ (AST, JSON, git,   │                  │ (spec ↔ case ↔ SUT     │
   │  report.xml)?      │                  │  source ↔ learnings)?  │
   └─────┬──────────────┘                  └───────┬────────────────┘
     yes │        │ no                          no │      │ yes
         ▼        ▼                                ▼      ▼
    ┏━━━━━━━━━┓  make it readable            don't add   ┏━━━━━━━━━┓
    ┃  LINT   ┃  first, then LINT            it at all   ┃  LENS   ┃
    ┃ engine/ ┃                                          ┃ agents/ ┃
    ┗━━━━━━━━━┛                                          ┗━━━━━━━━━┛
         ▲                                                    │
         └──────────── GRADUATION ◄───────────────────────────┘
              a lens finding that recurs becomes a lint
              (precedent: R-COVERAGE's metadata half → coverage_lint.py)
```

**"Don't add it at all"** is a real outcome and the most under-used one. A lens that fires on every
authoring run competes for attention with Tier 1; if it is noisy it gets waived, and a waived lens is worse
than no lens because it teaches the habit of waiving.

**Where a lint goes.** `engine/` — it is the AI-free deterministic core, and a gate belongs with the other
gates. Authoring *templates* stay out of `engine/` (spec 004 R5); that rule is about scaffolding, not about
gates.

## Concurrency model

Three shapes, and picking the wrong one is the usual mistake.

```
 SEQUENTIAL (barrier)          PARALLEL (fan-out)         PIPELINE (no barrier)
 ────────────────────          ──────────────────         ─────────────────────
   R-DIAGNOSIS                  R-EVIDENCE  R-MECHANISM     pack A ─► diag ─► verify
        │                            │          │           pack B ──► diag ─► verify
        ▼  must finish first         └────┬─────┘            pack C ────► diag ─► verify
   flags decide who runs next          barrier               each item flows
                                       ▼                     independently
                                 citation_gate
                                       ▼
                                     JUDGE

 WHY sequential: R-DIAGNOSIS's flags DECIDE whether the triage lenses run at all. Running
 them eagerly in parallel would spend two agents to save one agent's latency, and would
 produce findings on a failure nobody has understood yet.

 WHY the barrier before JUDGE: the JUDGE dedups ACROSS lenses. It genuinely needs every
 finding at once — one of the few real barriers in the repo.
```

The gate itself is parallel by a different mechanism: `tests/test_sites.py` runs under `pytest -n auto`,
one booted SUT **per xdist worker**, cases serial within a worker. That per-worker boot — not the
manifest's `isolate` hook, which runs *before* a case and fences nothing concurrent — is what makes
cases that share a server-global safe today. `[PROPOSED]` A shared-server or `remote` env removes that
isolation; packs that mutate shared state would need a serial lane.

## Worked examples

### E1 — Tier 1 suffices (the common case)

```
  cycle 1: a case's fixture raises on a response shape
     ├─ Tier 1: ORIENT (record) → engine/diagnostics.py → R-DIAGNOSIS → TEST_BUG, no flags, 1st cycle
     ├─ Tier 2 triggers: none → the panel does NOT run
     ├─ fix the case → fidelity_lint passes (the assertion is untouched) → re-run
     └─ report: `### Panel / - ran: R-DIAGNOSIS tier 1 (TEST_BUG, no flags)`
  cost: 1-2 agents
```

### E2 — Tier 2, the deterministic lens and the panel agreeing (SHOP-456)

The reference SUT ships a seedable regression precisely so this path is demonstrable:
`make diagnose-realbug` skips the discount branch while `BUSINESS_RULES` still declares it.

```
  gate red: SHOP-456 qty=3 leg — expected discount ~3.0, got 0.0; total ~27.0, got 30.0
     ├─ ORIENT: the pack README's off-by-one gotcha; the plan's Design panel record
     │          (F1 DEFERRED — "3 or more" summed across lines is not pinned)
     ├─ engine/diagnostics.py: claim rate 0.10 == contract rate 0.10, runtime violated it → REAL_BUG
     ├─ R-DIAGNOSIS: REAL_BUG, cited at sut/mock-shop/source/app.py — needs_mechanism set
     │               (does the discount branch fire at all?)
     ├─ Tier 2: R-MECHANISM verifies the rule and the threshold against the source
     ├─ citation_gate: every file:line resolves
     └─ JUDGE: REAL_BUG → a structured bug report for the HUMAN to file via the ticket provider.
               The test stays RED. Nothing is weakened.
  cost: 3-4 agents. Value: the test is correctly red, and the report is evidence-backed.
```

### E3 — Design panel, before code exists (the BOOK-UI-2 class)

```
  Phase 2b, plan drafted for a new UI pack
     ├─ [coverage_lint]  (where a pack exists) — does the metadata RESOLVE?
     ├─ R-DESIGN (Tier 1)
     │    · item 9: `covers` lists an endpoint the scenario never exercises   [FINDING]
     │      — exactly the BOOK-UI-2 defect (PR #26): the case was copied from
     │        BOOK-UI-1 and kept `POST /booking/`, which RESOLVES, so no lint
     │        could see it. Only a reader asks whether it is the RIGHT route.
     │    · item 2: the threshold is pinned on one side only                  [FINDING]
     │    · item 5: the pre-flight asserts what the case asserts → false-SKIP  [FINDING]
     └─ findings land in the EXISTING Phase-2 human gate, before a line of case
        code is written; the GENERATOR proposes a disposition per finding and
        [design_panel_lint] reconciles the count.

  Cost if found in Phase 4 instead: gate cycles, and a pack that looks covered.
```

### E4 — The deterministic orchestrator

`workflows/review-panel.js` implements the same protocol as a Workflow-tool script: ORIENT →
`engine.diagnostics` → R-DIAGNOSIS → flagged lenses in parallel → `engine.citation_gate` → JUDGE, with a
**subject gate** that throws rather than convening a panel against a null subject. It is human-triggered
(it spawns several agents); the model-driven path stays the always-on default. See `workflows/README.md`.

## Anti-patterns

| Anti-pattern | Why it is wrong | Instead |
|---|---|---|
| Inline self-triage on a failure | The exact bias the panel exists to check — correct labels still miss findings | Tier 1, always, as a subagent |
| Spawning a lens for a mechanical check | Non-determinism inside a regression suite | Write the lint, in `engine/` |
| Running every lens eagerly in parallel | Spends agents to save one agent's latency, on a failure nobody understands yet | Let R-DIAGNOSIS's flags decide |
| A lens verdict treated as a merge gate | Lenses are advisory; only the regression gate is truth | The human owns convergence |
| A subagent that commits, merges, or files a ticket | Breaks law 1 | It returns findings; the main agent acts |
| A JUDGE at Phase 2b | An adjudicator in front of the human approval gate; makes an advisory lens the design gate | The human ratifies the proposed dispositions |
| A "degraded/missing component" verdict from absence | Argument-from-absence; cross-lens consensus is not verification | A positive "expected-here" citation |
| Skipping the freshness gate on the on-demand path | How a citation against a stale clone gets trusted | The lens self-gates wherever it runs |
| A record lint that reports "clean" when it checked nothing | A silent pass is indistinguishable from a real one | Exit 2 when the scope cannot be determined (false-green-guard convention) |

## Cost model

| Path | Agents | When |
|---|---|---|
| Green run | 0 | the common case — no failure, no panel |
| Tier 1 only | 1-2 | most non-green results (ORIENT + R-DIAGNOSIS) |
| Tier 2 full panel | 3-5 | flags / REAL_BUG / 2nd cycle / reshape ack / a new pack's first landing |
| Design panel | 1-3 | once per pack, at Phase 2b |
| Orchestrated panel | 4-6 | human-triggered, via the Workflow tool |

The asymmetry that justifies the architecture: a subagent is minutes and read-only. A missed finding is a
gate cycle, a false escalation to whoever owns the backend, or a green gate carrying no signal.

## Related

- [review-panel.md](review-panel.md) — the protocol these dispatches follow on a failure
- [r-design.md](r-design.md) — the design-stage lens (row 3)
- [../quality-gates.md](../quality-gates.md) — every deterministic gate, with its exit codes
- [../../workflows/README.md](../../workflows/README.md) — the orchestrator (E4)
- `specs/005-design-panel-and-invocation-tiers.md` — the spec that added the design panel, the tiers and this doc
