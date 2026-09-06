# Spec 005 — Design panel (R-DESIGN), non-discretionary invocation tiers, ORIENT, and the deterministic panel orchestrator

> **Tracking**: [Calevi-Consulting/qensei#38](https://github.com/Calevi-Consulting/qensei/issues/38).
> Consistent with the existing top-level tooling specs (001–004), the filename stays numbered/ticketless.
> **Ownership**: internal — this touches the review-panel protocol, `commands/automate.md`, `engine/` gates
> and `agents/`; not a good-first-issue.
> **Provenance**: ported and adapted from the t-800 regression framework (`docs/multiagent/*`,
> `workflows/review-panel.js`, `tools/design_panel_lint.py`, `tools/panel_section_lint.py`, spec 026 WS-C),
> whose measured failure cases motivate every workstream below. Product-specific material (sidecar
> coalescing, IM offered load, `--dist=loadfile`, per-arm rollout, multi-repo routing) is deliberately
> **not** ported — `engine/`, `agents/` and `policies/` stay product-neutral.

## Status: COMPLETE

## Context

Qensei already carries the review panel's **back half**: seven advisory lenses (`agents/`), the Phase-4
protocol (`docs/multiagent/review-panel.md`: R-DIAGNOSIS → flag-gated R-EVIDENCE / R-MECHANISM → citation
gate → JUDGE), and four deterministic gates (`fidelity_lint`, `coverage_lint`, `citation_gate`,
`freshness_gate`). Three gaps remain, each with a measured cost in the framework this was ported from:

1. **The design stage has zero coverage.** Every lens fires in `/automate` Phase 4 — *after* a design
   defect has been implemented and has already cost gate cycles. `/automate` Phase 2b today is "write the
   plan, reference it from the spec": no review of the (spec, plan) pair before code exists. This repo has
   its own instance of the class: the BOOK-UI-2 defect (PR #26, spec 004 § Context) — a UI case copied from
   BOOK-UI-1 whose `covers` listed `POST /booking/`, an endpoint its scenario never exercises. A plan review
   asking "does `covers` name what the plan actually exercises?" catches that as a review comment, not a
   red gate.
2. **Panel invocation is discretionary prose.** `/automate` Phase 4b *lists* the lenses; nothing makes the
   driving agent dispatch them. The source framework measured the failure mode directly (2026-08-11): an
   inline triage that classified 3/3 failures **correctly** still missed **five** pre-merge findings the
   retroactive panel then surfaced. The panel's value is independent depth per lens, not the triage label
   — and *every deterministic gate fires every time while every remember-to instruction does not*. The one
   lens that did fire that day was the one wired to a lint.
3. **The lenses reason before reading the record.** Nothing in the protocol makes a lens read what the repo
   already knows about the failing pack — the index-card gotchas, the spec's ACs, `learnings/`, prior
   validation reports. Measured cost (2026-08-21, one run): a lens proposed REST filters that do not exist,
   cited the wrong line range, and re-opened a line of attack the pack README had already closed. All three
   were answerable from files in the repo.

A fourth item is an enabler rather than a gap: the protocol has one implementation (model-driven, the
agent *follows* the doc). A deterministic orchestrator (the Workflow tool) gives live observability,
structured findings, a **subject gate** (the source framework once spent ~160k subagent tokens convening a
panel against an all-null subject and got a confident `ESCALATE` back), and the citation gate as a real
step rather than "the JUDGE remembers".

## Requirements

- **R1 — Design panel at Phase 2b.** A read-only advisory lens, **R-DESIGN**, reviews the (spec, plan) pair
  after the plan is drafted and **before** any test code. Tiered exactly like Phase 4: lints first
  (`coverage_lint` where applicable), R-DESIGN always (Tier 1, as a subagent — inline self-review is not a
  substitute), R-MECHANISM / R-EVIDENCE on its `needs_mechanism` / `needs_evidence` flags (Tier 2). Findings
  surface at the **Phase-2 human approval gate that already exists** — no new gate, no merge authority, no
  slash command.
- **R2 — Findings come back into the design, traceably.** R-DESIGN returns at most six ranked findings
  labelled `F1..Fn`, each with its checklist item, a severity (`BLOCK-WORTHY` / `FIX` / `FLAG`), a
  `file:line` or an explicit `hypothesis:` label, and one concrete alternative. The **GENERATOR** records a
  *proposed* disposition per finding in the plan (`- F<n> APPLIED|REJECTED|FLAGGED|DEFERRED: <reason>`);
  the **human** ratifies at the approval gate. There is deliberately **no JUDGE at 2b** (a human is already
  one step away; an adjudicator in front of an adjudicator would make an advisory lens the de-facto design
  gate). R-DESIGN never writes a disposition.
- **R3 — The design-panel record is gated deterministically.** `engine/design_panel_lint.py` fails a
  **touched** plan (`sut/<name>/plans/*.md`) that carries no `## Design panel` section with `- ran: …` (+
  one disposition line per declared finding, labels `F1..Fn` each exactly once) or `- waived: <reason>`. It
  gates the **record, not the verdict**: `REJECTED` passes like `APPLIED`; a documented waiver passes.
- **R4 — Phase-4 invocation is tiered and non-discretionary.** Tier 1: **R-DIAGNOSIS runs as a subagent on
  every non-green gate result, before any fix.** Tier 2 (flagged lenses + citation gate + JUDGE) when ANY
  of: `needs_evidence` / `needs_mechanism` set · verdict `REAL_BUG` or `UNDOCUMENTED-ESCALATE` · the 2nd
  cycle on the same root cause · the fix needs a fidelity reshape ack (`--allow-reshape`) · the branch
  lands a **new pack** (its first landing). "The failure looks simple" is never a reason to skip Tier 1.
- **R5 — The panel record is gated deterministically.** `engine/panel_section_lint.py` fails a **touched**
  validation report that carries no `### Panel` section with `- ran: <digest / verdict ref>` or
  `- waived: <reason>`. Presence, not content; the human reads the waiver on the PR.
- **R6 — ORIENT before any lens reasons.** A read-only, best-effort step reads the **record** for the
  subject — pack index card (gotchas), spec ACs, plan(s), `sut/<name>/learnings/` + `skills/`, prior
  validation reports, the case source — and returns `sources_read`, `documented_disposition`,
  `rejected_fixes`, `known_traps`, `prior_attempts`, `acceptance_criteria`, `contradicts_subject`. It is
  **not a lens**: no verdict, no judgement. Every downstream prompt receives it (or an explicit "record
  absent — treat 'already known' claims as unestablished").
- **R7 — A deterministic orchestrator implements the protocol.** `workflows/review-panel.js` runs ORIENT →
  (deterministic `engine.diagnose` when a pack is named) → R-DIAGNOSIS → conditional parallel R-EVIDENCE /
  R-MECHANISM → `engine.citation_gate` as its own step → JUDGE, driving the **same** `agents/` lenses via
  `agentType`. It **throws** on a string or subject-less `args` (the subject gate) and requires `sut`.
  Wired as `.claude/workflows -> ../workflows` by `scripts/install.sh`. The model-driven path stays the
  default; the two coexist over one protocol doc.
- **R8 — The execution architecture is written down.** `docs/multiagent/execution-architecture.md`
  answers "at what moment does a subagent appear, under what condition, who decides?": the three laws,
  the cast (lenses vs lints, `[BUILT]` / `[PROPOSED]` marked), the `/automate` timeline with dispatches, the
  dispatch-conditions table, the lens-or-lint decision tree + graduation path, the concurrency model, the
  cost model, anti-patterns.
- **R9 — Product-neutral and zero-dependency.** The two lints are pure stdlib in `engine/` (the same home
  as the other gates), covered by `tools/tests/` (unittest), wired in pre-commit, `make check`, and the CI
  `checks` job. R-DESIGN's checklist names only framework concepts (personas, `requires` /
  `expect.precondition`, `covers` / `contract_claim`, durables, the SUTConnector, sourceless SUTs) — never
  one SUT's endpoints or rules.

## Acceptance Criteria

### WS-A — Design panel (R-DESIGN)

- [x] `agents/r-design.md` exists (read-only frontmatter matching the other lenses: `tools: Read, Grep,
  Glob, Bash`, `disallowedTools: Write, Edit, MultiEdit, NotebookEdit`), with a freshness self-gate
  (`make freshness SUT=…`; no-op for `in_process` / sourceless), a checklist covering at minimum: ticket
  scope → AC traceability (walk the ticket; two-signals-collapsed; existing-helper gravity) · ACs vs the
  risk the ticket carries · persona · REST-first vs UI · precondition ↔ assertion decoupling (the
  false-SKIP class: `requires` / `expect.precondition` asserting the same thing the case asserts) ·
  cross-pack reuse of durables · shared `existing_data` durables under parallel execution · write-then-read
  synchrony (→ `needs_mechanism`) · `covers` / `contract_claim` naming what the plan actually exercises ·
  the sourceless-SUT case (mapping cites the ticket/doc snapshot). Output contract per R2; hard limits:
  read-only, never weaken, advisory, **never writes a disposition**.
- [x] `docs/multiagent/r-design.md` documents the lens in the established per-lens shape (when it enters ·
  how its check works · what errors it must catch, including the BOOK-UI-2 / PR #26 case · the honest limit:
  bias errors yes, knowledge gaps no — recurring findings graduate to lints).
- [x] `commands/automate.md` Phase 2b documents the design panel as tiered and **non-discretionary**, in the
  same terms as Phase 4b, including the record requirement and who owns dispositions.
- [x] `engine/design_panel_lint.py`: `check_text()` passes `ran:` + matching `F1..Fn` dispositions, passes
  `ran:` with no declared count, passes `waived: <reason>`; fails a missing section, a missing entry, an
  empty entry, a declared count with fewer/more dispositions, duplicate or out-of-sequence labels, an
  unknown disposition word, a disposition without a reason, an unfilled `<placeholder>` value, an entry
  inside an HTML comment, and entries or dispositions outside the `Design panel` section. `is_lintable_path()`
  accepts `sut/<name>/plans/<file>.md` only. The failure message names the **proposal/human** ownership and says
  there is **no JUDGE** at 2b. Covered by `tools/tests/test_design_panel_lint.py` (unittest) pinning each
  polarity above.
- [x] The lint is wired: `.pre-commit-config.yaml` hook over `^sut/[^/]+/plans/.*\.md$` (pass_filenames), a
  `make design-panel` target scoped to plans changed vs `HEAD` **plus untracked ones** (a new plan is the
  common case), included in `make check`, and in the CI `checks` job scoped to the PR diff.
- [x] `agents/README.md` registry, `docs/multiagent/README.md`, `docs/diagnostics-and-review-panel.md`,
  `docs/quality-gates.md` (gate table), `CLAUDE.md`, and the generated `.claude/CLAUDE.md` index in
  `scripts/install.sh` name R-DESIGN and the new lint.

### WS-B — Invocation tiers + panel record

- [x] `docs/multiagent/review-panel.md` gains an **Invocation tiers** section (Tier 1 always / Tier 2
  triggers / the record row) with the under-invocation case study, and `commands/automate.md` Phase 4b
  states the tiers as non-discretionary (R-DIAGNOSIS as a subagent on every non-green result; inline
  self-triage is not a substitute).
- [x] `engine/panel_section_lint.py`: passes `### Panel` + `ran:`/`waived:` with content; fails a missing
  section, a missing entry, an empty entry, an unfilled `<placeholder>` value, an entry inside an HTML comment,
  and an entry outside the section — so **the real `TEMPLATE.md` content does not satisfy it** (pinned by
  test). `is_lintable_path()` accepts `validation-reports/*.md` and
  **rejects `validation-reports/TEMPLATE.md`** (the template shows the shape without satisfying the lint).
  Covered by `tools/tests/test_panel_section_lint.py`.
- [x] `validation-reports/TEMPLATE.md` carries a `### Panel` section with the two forms as guidance.
- [x] The lint is wired: pre-commit hook over `^validation-reports/.*\.md$`, a `make panel-record` target
  scoped to reports changed vs `HEAD` plus untracked ones, included in `make check`, and in the CI `checks` job.
- [x] `docs/quality-gates.md` lists both record lints with their exit codes.

### WS-C — ORIENT

- [x] `docs/multiagent/review-panel.md` adds the ORIENT step between the freshness gate and R-DIAGNOSIS
  (what it reads, the seven output fields, "not a lens", best-effort, and that `rejected_fixes` must not be
  re-proposed and `contradicts_subject` flags premises in the brief); `commands/automate.md` Phase 4b and
  `agents/judge.md` name the record as an input.

### WS-D — Deterministic orchestrator

- [x] `workflows/review-panel.js` exists with `meta` (name `review-panel`, four phases), the subject gate
  (throws on string `args`, throws when none of `failure|env|pipeline|spec|diff|pack` is supplied, throws
  when `sut` is missing), ORIENT (`general-purpose`), the deterministic `engine.diagnose` step when `pack`
  is given, R-DIAGNOSIS (`r-diagnosis`, verdict enum `TEST_BUG | REAL_BUG | ENV_OR_TRANSIENT | INDETERMINATE
  | UNDOCUMENTED-ESCALATE`, flags `needs_evidence` / `needs_mechanism`, `source_stale`), conditional
  parallel R-EVIDENCE / R-MECHANISM, a citation-gate step running `python3 -m engine.citation_gate` (exit
  0/1/3 mapped to resolved / fabricated / unverifiable), and JUDGE (`judge`, decision enum
  `BLOCK | FIX | FLAG | ESCALATE | PANEL_CLEAR`). Returns `{ decision, digest, record, diagnostics,
  diagnosis, lenses, citation_gate, verdict }`.
- [x] `workflows/README.md` documents invocation (`args` shape, `--sut` requirement, return shape) and why
  it coexists with the model-driven path.
- [x] `scripts/install.sh` symlinks `.claude/workflows -> ../workflows` alongside `commands` / `agents`, and
  the generated `.claude/CLAUDE.md` lists it.

### WS-E — Execution architecture

- [x] `docs/multiagent/execution-architecture.md` exists per R8, using qensei's cast (R-DESIGN, R-DIAGNOSIS,
  R-EVIDENCE, R-MECHANISM, R-COVERAGE, R-UPLIFT, JUDGE; lints `fidelity_lint`, `coverage_lint`,
  `citation_gate`, `freshness_gate`, `design_panel_lint`, `panel_section_lint`, the gate's false-green guard)
  and qensei's phases (`/automate` 0–5), with worked examples drawn from this repo (SHOP-456 seeded REAL_BUG;
  BOOK-UI-2 as the design-panel case).
- [x] `docs/multiagent/README.md` links it and states which of the three docs answers which question.

### Integration-boundary AC

- [x] **R-DESIGN has run for real, as a subagent, over a (spec, plan) pair in this repo** — a retro-plan
  authored for an existing `mock-shop` pack under `sut/mock-shop/plans/` — and the resulting plan carries a
  `## Design panel` record (real findings, real proposed dispositions) that `engine/design_panel_lint.py`
  passes. This exercises the actual dispatch path (`.claude/agents` wiring → subagent → findings → record →
  lint), not a mocked text check.
- [x] **The record lints fire through the real hook path**: with a scratch plan lacking the section staged,
  `make check` fails naming `[DESIGN-PANEL-RECORD-MISSING]`; with the section added it passes. Same for a
  scratch validation report and `[PANEL-SECTION-MISSING]`.
- [x] **The orchestrator has run end-to-end against the live in-process SUT**: `workflows/review-panel.js`
  invoked via the Workflow tool with `{ sut: "sut/mock-shop", pack: "sut/mock-shop/packs/SHOP-456-discount",
  seed_bug: true, failure: <the seeded REAL_BUG output> }` completed all four phases (6 agents, 0 errors),
  the citation-gate step's raw output is echoed verbatim in the JUDGE digest (18 anchors, exit 0, with a
  negative control proving non-vacuity), and the decision (`ESCALATE`) is recorded in the PR-2 validation
  report's `### Panel` line. The run also refuted the premise of its own brief and surfaced a verified
  framework-shape finding — see the report.

## Risks & Assumptions

- **A lens that fires on every authoring pass becomes noise, and noise gets waived** — a waived lens is
  worse than none (it teaches the habit). Mitigation: one Tier-1 lens at 2b, ≤6 findings, a one-line
  "nothing is wrong" is a valid answer, and every recurring finding **graduates to a lint** (precedent:
  R-EVIDENCE's mechanical halves became `freshness_gate` + `citation_gate`).
- **A count-match record is gameable** (`ran: 1 finding` + one line passes). Stated, not papered over: the
  lint raises the floor and cannot prove honesty; the human reads the record on the PR. The countervailing
  risk — a heavier format pushing authors toward `waived:` — is why the format is one line per finding.
- **No SUT has a `plans/` dir yet**, so the design-panel lint gates nothing until the first plan is written.
  The integration-boundary AC's retro-plan is the demonstrator and the first real record.
- **Changed-files-only scope**: existing plans / reports are never retro-gated (pre-commit
  `pass_filenames`; `make` targets diff vs `HEAD`; CI diffs vs the base ref). A file touched after this
  lands must carry its record.
- **The Workflow tool only runs when the user opts in** (it can spawn several agents). The orchestrator is
  therefore a human-triggered path; the model-driven protocol remains the default for `/automate` Phase 4.
- **Mid-session agent wiring**: a lens added to `.claude/agents` in a live Claude Code session registers but
  does not get its read-only tool limits until restart (documented in `agents/README.md`); R-DESIGN inherits
  that caveat.
- **Vocabulary drift between docs.** `review-panel.md` says `TRANSIENT`; `judge.md` and `diagnostics.py`
  say `ENV_OR_TRANSIENT` / `INDETERMINATE`. The orchestrator's schema uses the consumer's (JUDGE's) set; the
  protocol doc is aligned in the same change.
- **No runtime dependency is added** — the lints are stdlib; the workflow script is a Workflow-tool artifact,
  not a Python dependency. `engine/` stays the AI-free gate: the lints are deterministic text checks, no
  model in the loop.
- **Rollback**: every workstream is additive files + hook/Make/CI entries. WS-A/B: delete the lint, its
  test, its hook + target + CI line, and the doc paragraphs; the lens is advisory so nothing downstream
  depends on it. WS-C: revert the doc paragraphs. WS-D: delete `workflows/` and the symlink line. WS-E:
  delete the doc. Each PR reverts independently in minutes.

## Alternatives Considered

- **A JUDGE at Phase 2b.** Rejected: 2b already stops at a human one step later and fields one or two
  lenses with ≤6 findings — nothing for a judge to do that the approval gate does not; and it would make an
  advisory lens the de-facto design gate. Revisit only if 2b grows to ≥3 lenses with overlapping findings.
- **A `/design-panel` slash command.** Rejected on the same grounds as the review panel: a context-free
  trigger runs it with nothing concrete to review.
- **One lens per design concern** (persona, coverage, parallel conflicts, …). Rejected: most are
  deterministic and already are (or become) lints; extra lenses compete with Tier 1 for attention and get
  waived.
- **Port `ac_coverage_lint` / `scope_coverage_lint` (AC→case and ticket→AC binding by explicit id) in this
  spec.** Deferred to a follow-up: qensei specs carry no `**AC<n>**` ids and `RegressionCase` has no binding
  field, so it touches `engine/case.py`, the scaffolder and the spec convention — a separate design decision.
  R-COVERAGE already covers the semantic half; R-DESIGN checklist item 1 covers the ticket walk.
- **Put the record lints under `scripts/` / `tools/`.** Rejected: they are deterministic gates with the same
  contract as `fidelity_lint` / `coverage_lint` (identical input → identical verdict, exit-code enforced),
  and gates live in `engine/`. Spec 004's R5 excludes *authoring templates* from `engine/`, not gates.

## Phasing

- **PR 1 — WS-A + WS-B + WS-C** (the complete "review panel before and after implementation, with a
  gated record"). Lands the two lints first (deterministic floor), then the lens, then the protocol/ORIENT
  doc changes, then the demonstrator retro-plan.
- **PR 2 — WS-D + WS-E** (the orchestrator + the architecture doc), once PR 1 has settled the vocabulary
  the script encodes.

## Executive Summary

**PR 1 (WS-A + WS-B + WS-C).** Adds the panel's front half and makes its back half non-discretionary. A new
design-stage lens, **R-DESIGN**, reviews the (spec, plan) pair at `/automate` Phase 2b before any pack code
exists; its findings come back into the plan as a per-finding record (`F<n> APPLIED|REJECTED|FLAGGED|DEFERRED`)
that `engine/design_panel_lint.py` gates for presence and count — the GENERATOR proposes, the human ratifies,
no JUDGE at 2b. Phase-4 invocation is now tiered (R-DIAGNOSIS as a subagent on every non-green result; the full
panel on flags / `REAL_BUG` / 2nd cycle / reshape ack / a pack's first landing) and recorded in every
validation report, gated by `engine/panel_section_lint.py`; an ORIENT step returns the repo's record before any
lens reasons. Exercised for real: R-DESIGN ran three times over a SHOP-456 retro-plan (two runs 4/4 consistent,
R-MECHANISM 7/7 CITED, every citation resolving), and the hook path was driven to both polarities. Reviewers
should look first at `engine/design_panel_lint.py` + its tests, `agents/r-design.md`, and the demonstrator's
`## Design panel` record in `sut/mock-shop/plans/`.

**PR 2 (WS-D + WS-E).** Adds the protocol as a deterministic Workflow-tool script
(`workflows/review-panel.js`: ORIENT → `engine.diagnostics` → R-DIAGNOSIS → flagged R-EVIDENCE / R-MECHANISM
in parallel → `engine.citation_gate` → JUDGE, with a subject gate that throws rather than convening a panel
against a null subject) and the timeline doc that says when each dispatch happens and who decides
(`docs/multiagent/execution-architecture.md`: three laws, the cast, the gate table with exit codes, the
dispatch-conditions table, the lens-or-lint tree and its graduation path, worked examples from this repo).
The orchestrator was run for real against the live in-process SUT: it refuted the false premise in the brief
it was handed, declined to file a bug and said why, surfaced the deterministic-lens / R-DIAGNOSIS
disagreement without resolving it, and produced one verified framework-shape finding (a seeded gate red is
indistinguishable from a genuine one in the artifact) that is left with the human. Reviewers should look
first at `workflows/review-panel.js` (the subject gate and the two mechanical steps) and at the PR-2
validation report's account of that run.
