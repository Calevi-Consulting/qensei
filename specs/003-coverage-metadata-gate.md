# Spec 003 — Coverage-metadata gate (`engine/coverage_lint.py`)

> **Tracking issue**: [Calevi-Consulting/qensei#27](https://github.com/Calevi-Consulting/qensei/issues/27).

## Status: INCOMPLETE

> **Phase A delivered** (`engine/coverage_lint.py` + tests + wiring): AC0–AC12, AC14 met and checked.
> **Phase B pending** (AC13 — the R9 process backstop: non-skippable `r-coverage` in
> `commands/automate.md` Phase 4b + PR-template attestation). Status stays INCOMPLETE until Phase B
> lands, per the Phase-6.5 reconciliation rule (do not flag COMPLETE with an unchecked criterion).

## Context

Every deterministic gate the framework owns has a blind spot for a **brand-new pack**.
`fidelity_lint` is an AST diff against the git baseline, so a pack with no blob at `HEAD`
returns zero findings (`engine/fidelity_lint.py:117-119`) — by design it only catches
*weakening* of an existing pack. `design.py` computes the coverage gap **forward only**
(source routes/rules no pack covers, by set difference at `engine/design.py:41-42`); it never
validates that a `covers` token resolves to a real route, and never opens the pack's README or
spec. `citation_gate` / `freshness_gate` are out of scope (lens-citation anchors / source-clone
freshness). The only component that cross-checks `covers` / `contract_claim` ↔
`ROUTES` / `BUSINESS_RULES` ↔ acceptance criteria is the **advisory, human-invoked** `r-coverage`
lens — absent from CI, and by construction "raise the floor, never gate a merge".

The trigger was PR #26 (`BOOK-UI-2-validation-error`): a brand-new UI pack whose `case.py` was a
verbatim copy of `BOOK-UI-1`'s happy path, diverging from its own README/spec — including a
`covers` list that disagreed with the README. It passed CI green because nothing deterministic
reconciled the two.

This spec adds `engine/coverage_lint.py`, the deterministic companion `agents/r-coverage.md`
already reserves by name: a gate that runs on **every** pack with **no git baseline** and blocks a
merge when a pack's declared coverage metadata is internally inconsistent, dangling, or (on a
source-backed SUT) unresolvable against the SUT source.

**Scope boundary — symptom, not disease.** The gate blocks the *covers-drift artifact* of the
PR #26 class (a `covers` list that disagrees with the README, or resolves to nothing). It does
**not** catch the semantic defect that a `run()` body exercises the wrong behaviour — that is
`r-coverage`'s advisory GAP verdict and a human review ritual (R9). The gate raises the floor; it
does not replace the lens.

**Prior work already landed.** The empirical audit surfaced one real pre-existing drift —
`SHOP-DUR` declared `GET /accounts/{id}` while the source route is `GET /accounts/{name}`. That fix
shipped in **#28** (merged), so `covers`-validity is green on all three SUTs today; the "same-PR
data fix" constraint the tracking issue noted is already satisfied.

## Requirements

- **R0 (governing invariant — product-neutrality)** — `engine/coverage_lint.py` reads
  `covers` / `ROUTES` / `BUSINESS_RULES` **only** through `SUTConnector`
  (`source_module` / `source_path` / `has_source`) and locates packs/specs via
  `packs_dir` / `ui_packs_dir` / `specs_dir`, deriving the SUT name from the pack path. It never
  hardcodes any SUT's endpoints, rules, or skills. The real neutrality trap is the Markdown parser,
  not the code: it MUST accept the observed **union** of authoring styles and never impose one SUT's
  house style (see R6). Baking a single style into `engine/` would invert the framework promise
  "adding a product is writing a plugin, never touching `engine/`".
- **R1 (the module)** — a new `engine/coverage_lint.py`, pure Python 3 stdlib, exit-coded (`0` pass /
  `1` any BLOCK; `2` no packs discovered, the false-green-guard convention). It discovers packs
  through **each SUT's declared `packs_dir` / `ui_packs_dir`** (via `SUTConnector`, per R0 — never the
  literal `packs`/`ui-packs` names, so a SUT that customises `tests.packs` is not silently skipped),
  pairs each `case.py` with its sibling `README.md` and its `spec_ref`-resolved `specs/<ID>.md`, and
  **evaluates every pack unconditionally with no git baseline** — the structural property that closes
  the new-pack blind spot shared by `fidelity_lint` (baseline diff) and `design.py` (forward-only). It
  reuses `fidelity_lint`'s AST helpers (`_cases` / `_attr` / `_eval_value`, which read
  `covers` / `contract_claim` / `spec_ref` without importing `case.py`) and `design.py`'s
  `has_source` branch. Explicit paths (a pre-commit hook passing changed `case.py`/`README.md` files)
  are mapped to their pack dir directly, so the hook is dir-name-agnostic.
- **R2 (covers-consistency — BLOCK)** — the AST-extracted `case.py` `covers` set must equal the
  sibling README `Covers:` token set. This is a **cross-check of two independently-authored copies,
  never a derivation** (see Alternatives). Governance decision: this is a hard BLOCK (a dissent
  argued for WARN — recorded in Alternatives).
- **R3 (covers-validity — BLOCK, source-backed SUTs only)** — every `covers` token must resolve to a
  real ROUTE (`f"{METHOD} {path}"`) or a `BUSINESS_RULES` id, by exact-string membership (no
  path-param normalization — the `SHOP-DUR` `{id}`-vs-`{name}` case proves exact matching catches
  real bugs `design.py` already miscounts).
- **R4 (contract_claim resolution — BLOCK, source-backed SUTs only)** — a case's `contract_claim`
  rule id must exist in `BUSINESS_RULES`; prevents `diagnose` misclassifying REAL_BUG / TEST_BUG
  against a fabricated rule.
- **R5 (spec_ref resolves — BLOCK)** — every case's `spec_ref` must point to an existing
  `specs/<ID>.md` under that SUT's `specs_dir`. This is `r-coverage`'s CLAIM-MISMATCH item made
  deterministic.
- **R6 (README Covers line present-and-parseable — BLOCK)** — a pack whose README has no parseable
  `Covers:` line fails, turning the currently-informal convention into an enforced one. The parser
  MUST tolerate both observed forms: `- Covers:` (8 packs) and `- **Covers:**`
  (`sut/widget-api`).
- **R7 (sourceless degradation)** — branch on `has_source` **before** any `source_module()` call
  (`_require_source()` raises `ValueError` for a sourceless SUT — `engine/sut.py:264-280`). When
  `has_source` is False (`widget-api`): SKIP covers-validity (R3) and contract_claim resolution (R4)
  and report each as `UNVERIFIED (sourceless)` — never FAIL. The source-independent checks
  (R2 consistency, R5 spec_ref, R6 README-Covers-present) **still run and still gate**.
- **R8 (duplicate-body detector — WARN only)** — an AST fingerprint (`ast.dump` of the `run()` body,
  docstring stripped) that flags a `run()` body **verbatim (modulo docstring)** to a sibling's (it
  would flag `BOOK-UI-2` as a copy of `BOOK-UI-1`). It is deliberately a WARN, not a BLOCK: legitimate
  parametric sibling packs can be near-identical, and a copy with any real edit (a renamed variable, a
  changed literal) evades the exact fingerprint — so it is a best-effort second net surfaced for a
  human (exit `0`), never a gate.
- **R9 (semantic backstop — process, never a merge gate)** — the AC-exercise question ("does `run()`
  actually drive the behaviour each acceptance criterion means?") stays with `r-coverage`'s GAP
  verdict; it is inherently semantic and must not sit in a deterministic gate seat. Make it
  **non-skippable by process**: `commands/automate.md` Phase 4b cannot reach the exit gate until
  `r-coverage` has run and any GAP is surfaced, and the PR template carries a human attestation line
  ("`r-coverage` run on new/changed packs; any GAP resolved or explicitly accepted by a human").
- **R10 (wiring)** — (a) **non-negotiable:** a new step in the `qa-gate.yml` `checks` job (the only
  job that runs on fork-branch PRs, and it runs individual steps — it does not invoke
  `make check`/`verify`); (b) a `coverage-lint` Makefile target folded into `check` and `verify`
  (stays offline/stdlib); (c) a `.pre-commit-config.yaml` hook on
  `^sut/.*/(packs|ui-packs)/.*/(case\.py|README\.md)$` (fires on a new pack — no baseline no-op).
- **R11 (tests)** — stdlib `unittest` cases in `tools/tests/` covering every gated and non-gated
  behaviour, including a reconstruction of PR #26 (BLOCK), the co-copied-README fragility case
  (all gated checks green, dup-detector WARN), dual-format Covers parsing against the real widget-api
  string, sourceless degradation end-to-end, and a new-pack-without-git-baseline case.

## Acceptance Criteria

- [x] **AC0** — `engine/coverage_lint.py` exists, is pure Python 3 stdlib (no runtime deps), and
  exits `0` on pass / `1` on any BLOCK finding; a WARN finding alone exits `0`.
- [x] **AC1 (no regression)** — running it over the current tree (with #28 already merged) exits `0`:
  green on `mock-shop`, `restful-booker`, and `widget-api`.
- [x] **AC2** — covers-consistency: a pack whose `case.py` `covers` set differs from its README
  `Covers:` token set produces a BLOCK naming the pack and the differing tokens; a reconstruction of
  PR #26's `BOOK-UI-2` (`case.py` covers `[GET /ui, GET /room/, POST /booking/]`, README
  `[GET /ui, GET /room/]`) is BLOCKed.
- [x] **AC3** — the README `Covers:` parser accepts both `- Covers:` and `- **Covers:**`;
  `widget-api`'s bold line and the plain lines all parse to the correct token set (no false BLOCK on
  `widget-api`). Fixtures use the real observed strings.
- [x] **AC4** — a README with no parseable `Covers:` line produces a BLOCK.
- [x] **AC5** — covers-validity (source-backed SUT): a `covers` token resolving to neither a ROUTE nor
  a `BUSINESS_RULES` id produces a BLOCK. (A regression fixture reproduces `SHOP-DUR`'s pre-#28
  `GET /accounts/{id}` against source `GET /accounts/{name}` and asserts BLOCK; the live tree passes
  post-#28.)
- [x] **AC6** — contract_claim (source-backed SUT): a `contract_claim` rule id absent from
  `BUSINESS_RULES` produces a BLOCK; the 3 packs carrying a real rule id pass.
- [x] **AC7** — spec_ref: a case whose `spec_ref` names no existing `specs/<ID>.md` under its SUT
  produces a BLOCK; all current `spec_ref`s resolve.
- [x] **AC8 (sourceless degradation)** — for a `has_source == False` SUT, covers-validity and
  contract_claim resolution are SKIPPED and reported `UNVERIFIED (sourceless)` (never FAIL);
  consistency, spec_ref-resolves, and README-Covers-present still run and still gate;
  `source_module()` is never called on a sourceless SUT (no `ValueError`). Asserted end-to-end on
  `widget-api`.
- [x] **AC9 (new-pack, no baseline)** — the gate evaluates a pack present in the working tree but not
  at `HEAD`, proving it does not share `fidelity_lint`'s baseline blind spot.
- [x] **AC10 (duplicate-body)** — the detector emits a WARN (exit `0`) when a `run()` body is
  near-identical to a sibling's (`BOOK-UI-2` vs `BOOK-UI-1`) and never a BLOCK for it.
- [x] **AC11 (fragility, encodes the admitted limitation)** — a co-copied-README variant where
  `case.py` and README agree on the *wrong* `covers` → all gated checks stay GREEN and only the
  duplicate-body detector WARNs. This fixes the known evasion as a test, not prose.
- [x] **AC12 (integration-boundary — real SUT tree)** — the gate is exercised against the **actual**
  `sut/*` tree (all three real SUTs, resolving `covers` against the real `source_module()` for the
  two source-backed ones and degrading for the sourceless one), not a mock of the source — and is
  wired as its own step in the `qa-gate.yml` `checks` job (runs on every push/PR incl. forks) and as
  a `coverage-lint` target in `make check` / `make verify`, with a matching pre-commit hook.
- [ ] **AC13 (process backstop)** — `commands/automate.md` Phase 4b makes `r-coverage`
  non-skippable before the exit gate, and the PR template carries the `r-coverage` / GAP
  human-attestation line.
- [x] **AC14** — `tools/tests/` contains stdlib `unittest` cases covering: consistent-pass,
  inconsistent-block, unresolvable-cover-block, contract_claim-mismatch-block, dangling-spec_ref-block,
  missing-Covers-line-block, both-Covers-formats-parse, sourceless-skips-validity-runs-consistency,
  duplicate-body-warn-not-block, co-copied-README-fragility, and new-pack-no-baseline.

## Risks & Assumptions

- **Consistency is a cross-check, so a co-copied README defeats it.** Had the PR #26 author also
  copied `BOOK-UI-1`'s README, all gated checks would go green. This residue is covered by the
  process backstop (R9) and the WARN-only dup-detector (R8), **not** by the gate. Surfaced (AC11),
  not hidden.
- **Exact-string covers↔ROUTE matching has no path-param normalization.** A future `{id}` / `{name}`
  / `{bookingid}` spelling skew between a cover and its ROUTE trips validity — this *is* the drift
  class the gate exists to catch (it mirrors `design.py`'s membership semantics), but it means source
  path-param renames require the covers/README to be updated in lockstep.
- **Two hand-authored copies impose a small authoring burden** (the opposite of the rejected derive
  approach) — accepted as the price of retaining the divergence detector.
- **The Markdown parser is the neutrality risk.** A parser recognizing only the majority `- Covers:`
  form would false-RED `widget-api` — an adoption blocker and a house-style leak into `engine/`.
  Mitigated by R6 + AC3 (tolerate both, tested against the real bold string).
- **Irreducible sourceless blind spot.** A sourceless pack can declare a bogus cover and no
  deterministic check catches it — consistency only proves two copies *agree*, never that either is
  *correct*; the ticket is the contract of record. Stated plainly, not papered over.
- **Governance decision recorded** — covers-consistency is a BLOCK (R2). The alternative (WARN +
  non-skippable `r-coverage`) is legitimate and documented; the choice is BLOCK because it is the
  only deterministic check that catches the PR #26 artifact and its false-positive rate is near-zero.
- **Rollback:** entirely additive — a new module + four wiring points + process edits. Revert removes
  the module and its CI/Makefile/pre-commit hooks; no existing behaviour changes.

## Alternatives Considered

- *Derive the README `Covers:` line from `case.py` (single source of truth).* **Rejected** — it would
  regenerate the README to match a wrong `case.py`, turning red green and burying exactly the
  divergence reviewers noticed in PR #26. Keep the two as independent copies and gate their equality;
  the disagreement is the diagnostic signal.
- *covers-consistency as WARN + non-skippable `r-coverage` (the over-gating dissent).* Honours the
  strict engine/lens split (consistency is a doc-sync check, not oracle-backed) and is evadable, but
  demoting it to WARN means **nothing** deterministic catches the PR #26 artifact. Rejected in favour
  of BLOCK, given the near-zero false-positive rate; recorded as an explicit governance decision.
- *A deterministic AC-exercise / behaviour check.* Rejected — deciding whether `run()` exercises an
  acceptance criterion is inherently semantic and cannot sit in a deterministic gate seat; it stays
  with `r-coverage` (R9).
- *Gate spec-status integrity now (COMPLETE ⟹ all AC `[x]`; COMPLETE ⟹ referenced by a pack).*
  Deferred (see Phasing) — valuable and green today, but the status vocabulary is not yet uniform
  (`## Status:` heading vs a `| Status | … |` table row — `SHOP-DUR` uses only the row, so a
  heading-only parser is a false negative), and it would **not** have caught PR #26 (that spec is
  COMPLETE, boxes checked, referenced by a pack).

## Phasing

- **Phase A (this spec) — the gate.** R0–R7, R10–R11 and the day-one hard gate (covers-consistency,
  covers-validity, contract_claim, spec_ref, README-Covers-present) with sourceless degradation, plus
  the WARN duplicate detector (R8). Acceptance criteria AC0–AC12, AC14.
- **Phase B (fast-follow, same module) — the process backstop + spec-status integrity.** R9
  (`automate.md` Phase 4b + PR-template attestation — AC13), and the deferred Phase-6.5 spec-status
  checks once the status vocabulary is normalized or the parser provably tolerates both forms.

## Amendments

Changes to the **requirement text** made after the spec was first committed (#29), recorded here for
traceability rather than folded silently into implementation. Both were surfaced to and approved by
the maintainer during the Phase-A implementation (#30); neither weakens an acceptance criterion.

- **A1 — R1 discovery (was: literal glob).** As first written, R1 said the gate "globs
  `sut/*/packs/*/case.py` + `sut/*/ui-packs/*/case.py`". This contradicted **R0**, which already
  required locating packs via each SUT's `packs_dir` / `ui_packs_dir`, and the literal glob carried a
  latent false-GREEN: a SUT that customises `tests.packs` in its manifest would have all its packs
  silently skipped. R1 was reconciled to R0's already-stated intent — discovery through each SUT's
  declared dirs (via `SUTConnector`), with explicit pre-commit paths still mapped to their pack dir.
  *Rationale:* fix a spec self-contradiction and close the false-GREEN; strictly more coverage, not less.
- **A2 — R8 wording (was: "near-identical").** R8's "flags a `run()` body near-identical to a
  sibling's" was tightened to "**verbatim (modulo docstring)**", matching what an `ast.dump`
  fingerprint can actually decide, and R8 now states plainly that a copy with any real edit evades it —
  so the WARN-only status is honest about the heuristic's reach. *Rationale:* accuracy; no behavioural
  change (it was always a WARN, never a gate).

## Executive Summary

*(Provisional — to be finalized before the implementation PR.)* `engine/coverage_lint.py` is a
deterministic, pure-stdlib gate that reconciles each pack's `case.py` coverage metadata with its
README and spec, running on **every** pack with **no git baseline** — the property that closes the
new-pack blind spot which let PR #26 pass CI green. It hard-gates the reproducible invariants
(`covers` case↔README consistency, `covers`/`contract_claim` resolution against the SUT source,
`spec_ref` resolves, README `Covers:` present) and degrades cleanly for sourceless SUTs via
`has_source` (skip validity, emit `UNVERIFIED`, never call `source_module()` unguarded). The
semantic half — whether `run()` exercises each acceptance criterion — stays with the advisory
`r-coverage` lens, made non-skippable by process rather than pretended into a gate. Reviewers should
look first at `engine/coverage_lint.py` (reuse of `fidelity_lint`'s AST helpers + `design.py`'s
`has_source` branch), the dual-format README parser (the product-neutrality trap), and the proofs in
`tools/tests/` — especially the PR #26 reconstruction (BLOCK) and the co-copied-README fragility case
(green + dup-WARN).
