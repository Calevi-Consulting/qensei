# Spec 001 — Sourceless, ticket-driven mode with optional documentation

> **Tracking issue**: [Calevi-Consulting/qensei#14](https://github.com/Calevi-Consulting/qensei/issues/14).

## Status: INCOMPLETE

## Context

Qensei is "backend-aware": `design` reads `ROUTES` / `BUSINESS_RULES` from the SUT
**source**, `diagnose` classifies REAL_BUG vs TEST_BUG against that source, and the gate
runs cases against the live **runtime**. Some products cannot expose their source to
Qensei, yet a running instance is reachable and the intent lives in tickets (Jira) with,
sometimes, product/change documentation.

This spec adds a **sourceless mode**: a SUT operates with **no source code**, while its
**live runtime still backs the regression gate**. The contract / system-shape authority
shifts to the **ticket plus whatever documentation is available**. It also closes two
input-ingestion gaps (R6–R7).

**Guiding principle — best-effort composition + honest precision.** The non-runtime inputs
are a spectrum, and every one of them is optional. Qensei composes from whatever is present
(ticket description / AC / comments, product docs, change docs) and is explicit about the
resulting precision: more inputs → more precise cases; fewer inputs → do what is possible and
say so. It must never claim source-grounded confidence it does not have. **Conversely, source presence
reverts everything to the original strict behavior** — the sourceless path is a strictly-gated fallback,
never a relaxation of the source-backed one (see R0).

Scope (confirmed with the maintainer):

- The **runtime IS available**; only the source is absent. (A no-runtime, design/authoring-only
  mode is a separate, later iteration.)
- **Documentation is optional** and may be partial or missing per ticket. Near-term it lives as
  files in the SUT plugin (`sut/<name>/skills/` + `learnings/`, already loaded on demand) and/or
  as links/attachments on the ticket (`ticket.links[]`). A live external docs provider
  (Confluence / PDF fetch) is deferred.
- "Codebase-optional" means the **source**, not the runtime.

## Requirements

- **R0 (governing invariant)** — Source presence is detected per SUT. **When the source is present, all
  validation is exactly the original strict behavior**: hard `r-diagnosis`, hard `r-fidelity`, the
  deterministic `diagnostics.py` compared against `BUSINESS_RULES`, `source:line` citations, and
  `citation_gate` + `freshness_gate` over the source clone. The sourceless path (R4–R5, R12–R13, degraded
  lenses) is a **strictly-gated fallback that is unreachable for a source-backed SUT** — it never relaxes
  the source-backed path.
- **R1** — A SUT can declare it has no source (manifest `source` omitted or `source.mode: "none"`);
  the framework treats it as **sourceless**.
- **R2** — The regression gate runs unchanged for a sourceless SUT against its live runtime; the
  false-green guard (empty / all-skipped / unreachable / creds-unresolved → exit 2) still holds.
- **R3** — The SUT-source **freshness gate** (`source_sync` / `freshness_gate` / `/automate`
  Phase 0 step 4) is a no-op for sourceless SUTs, without weakening it for source-backed SUTs.
- **R4** — `design` degrades gracefully with no source: instead of source `ROUTES` / `BUSINESS_RULES`
  gap analysis, it derives candidate coverage from the ticket's acceptance criteria plus any
  available docs; it states the surface came from ticket/docs, not source; no crash, no misleading
  "fully covered".
- **R5** — `diagnose` with no source classifies a failure against the **ticket-declared contract**
  (the case's `contract_claim` resolves to the ticket AC / documented rule) and **labels the
  contract of record as the ticket**, not source `BUSINESS_RULES` (weaker independence — see Risks).
- **R6** (Gap 1) — `/automate` reads the ticket's **comments** chronologically (mirroring `/validate`)
  and folds scope / AC / edge-case signals into the human-approved spec; it never silently rewrites
  the human's AC.
- **R7** (Gap 2) — `/automate` accepts a ticket **validated outside Qensei**: entry premise + Phase 3
  state validation evidence may come from a `/validate` run OR the ticket itself (description + AC +
  comments + status); no prior `/validate` run is required.
- **R8** — **Documentation is optional and best-effort.** When product/change docs are present (SUT
  `skills/` files and/or ticket `links[]` / attachments), Qensei uses them to make cases more precise
  and to inform the contract; when absent, it proceeds with the ticket alone and records reduced
  precision. Missing docs are never a hard failure.
- **R9** — The normalized-ticket vocabulary (`ticket/contract.md`) gains `comments[]`; the mock-file
  format documents a `## Comments` section; the Jira provider documents `comments[]`; `/validate` and
  `/automate` share the same shape.
- **R10** — A worked example: a sourceless demo SUT that runs the gate against a live/mock runtime
  with the ticket (+ optional docs) as the contract source, exercised in CI.
- **R11** — Docs (README / overview / CLAUDE.md + the promo framing) describe backend-source as **one**
  mode, not the only one; `sut/contract.md` documents the sourceless declaration and the optional-docs
  model.
- **R12** — **Sourceless Phase-4 triage.** *(Phase A)* The deterministic `engine/diagnostics.py` lens,
  lacking `BUSINESS_RULES`, resolves the case's `contract_claim` against the **ticket-declared rule** when
  the claim references one, and otherwise returns `INDETERMINATE` (never a `REAL_BUG` / `TEST_BUG` inferred
  off an absent oracle). *(Phase A)* The source-citing lenses (`r-mechanism`, `r-evidence`, `r-coverage`)
  **degrade explicitly** — they announce "source absent; finding advisory, not source-verified" and emit no
  `source:line`. *(Phase B)* Those lenses instead **retarget** their citations to a **ticket/doc anchor**
  (ticket AC / comment id / doc section). `r-diagnosis` reads ticket + docs + skills + spec in place of the
  source in both phases.
- **R13** *(Phase B)* — **Anti-fabrication + freshness retarget to a ticket/doc snapshot.** Qensei snapshots the
  fetched ticket (and any consumed docs); `citation_gate` resolves every cited ticket/doc anchor against
  that snapshot (so a fabricated / unresolvable anchor fails exactly as a bad `source:line` does today),
  and `freshness_gate` validates the snapshot's currency instead of a source-clone `HEAD`. Source-backed
  SUTs keep the existing `source:line` + clone-freshness behavior.
- **R14** — The prime invariant is unchanged: `r-fidelity` / `fidelity_lint` still block silently
  weakening an acceptance criterion to go green, identically in sourceless mode (it is orthogonal to the
  source).

## Acceptance Criteria

- [ ] **AC0 (no regression)** — source-backed SUTs (`mock-shop`, `restful-booker`) behave **identically**
  to before: same gate results, same `diagnostics.py` verdicts, hard `r-diagnosis` / `r-fidelity`,
  `source:line` citations + freshness enforced. A test asserts the sourceless branch is never taken when
  source is present.
- [ ] **AC1** — a SUT manifest can declare no source; `SUTConnector.source_module()` / `source_path()`
  and all callers handle its absence cleanly (no exception, no silent wrong behavior).
- [ ] **AC2** — **[integration-boundary]** `make test SUT=<sourceless>` runs cases against the **real
  runtime** and reports PASS/FAIL/SKIP with correct exit codes; empty / all-skipped / unreachable still
  trips the false-green guard (exit 2).
- [ ] **AC3** — the source-freshness gate is a no-op for a sourceless SUT and still enforced for a
  source-backed SUT (engine unit test covers both).
- [ ] **AC4** — `python3 -m engine.design --sut <sourceless>` produces candidate coverage from ticket
  ACs (+ docs if present), states the surface origin, and does not crash or report a misleading
  "fully covered".
- [ ] **AC5** — a seeded failure on a sourceless SUT is diagnosed against the ticket-declared contract,
  with output explicitly labeling the ticket as the contract of record.
- [ ] **AC6** — missing documentation is handled gracefully: the flow works with docs present (more
  precise) and absent (ticket-only); the absence is reported, not errored (test covers both).
- [ ] **AC7** — `ticket/contract.md` defines `comments[]`; mock-file parses a `## Comments` section;
  `commands/automate.md` Phase 1 reads comments and folds them into the spec draft.
- [ ] **AC8** — `commands/automate.md` no longer requires a `/validate` artifact; entry premise +
  Phase 3 accept ticket-borne validation evidence.
- [ ] **AC9** — a sourceless SUT fixture runs green in `qa-gate` (CI).
- [ ] **AC10** — docs updated (README / overview / CLAUDE.md / `sut/contract.md`) for the sourceless +
  optional-docs model; CHANGELOG Unreleased entry; existing gates stay green.
- [ ] **AC11** — in sourceless mode, `engine/diagnostics.py` never emits `REAL_BUG` / `TEST_BUG` off an
  absent `BUSINESS_RULES`: it resolves `contract_claim` against the ticket-declared rule or returns
  `INDETERMINATE` (engine unit test).
- [ ] **AC12** — `citation_gate` resolves ticket/doc-anchored citations against the ticket/doc snapshot
  for a sourceless SUT (and still resolves `source:line` for a source-backed SUT); a fabricated /
  unresolvable anchor fails the gate (test).
- [ ] **AC13** — `freshness_gate` validates the ticket/doc snapshot's currency for a sourceless SUT and
  the source-clone `HEAD` for a source-backed SUT.
- [ ] **AC14** — the `agents/` lens docs (`r-mechanism`, `r-evidence`, `r-coverage`, `r-diagnosis`)
  state their sourceless behavior (cite ticket/doc anchors; degrade explicitly); `r-fidelity` unchanged.

## Risks & Assumptions

- **Diagnose loses independence (the key trade-off).** With no source, the ticket/docs are BOTH the
  test's origin AND the contract authority. Diagnose can then only assert "the running system violates
  the stated ticket contract" (a candidate REAL_BUG); it can no longer separate a TEST_BUG from a
  *wrong ticket*, because there is no independent oracle. Mitigation: diagnose **labels** this
  explicitly (contract of record = ticket) instead of claiming the old REAL/TEST confidence. Humans
  own the ticket/doc contract.
- **Design/precision scales with inputs.** Ticket-only → coverage is "criteria not yet covered"
  relative to the ticket, not the true backend surface; it cannot find endpoints/rules the inputs
  never mention. Surfaced, not hidden.
- **Anti-fabrication is weaker in sourceless mode.** Resolving a citation against the ticket/doc
  snapshot proves the lens did not invent the claim *relative to the ticket* — but the ticket is also
  the test's origin, so this is a weaker guarantee than resolving against an independent source. The
  circularity is inherent; it is surfaced (the "contract of record = ticket" label + the `INDETERMINATE`
  verdict), not papered over.
- **Runtime still required** — this mode does not cover the no-runtime case (deferred).
- **Live external docs provider deferred** — docs are files-in-plugin and/or ticket links for now.
- **Rollback:** entirely additive — a new sourceless declaration + optional-doc handling; source-backed
  SUTs are unchanged. Revert removes the sourceless branch/flag.

## Alternatives Considered

- *No-runtime, design/authoring-only mode.* Deferred — maintainer scoped to runtime-available.
- *A live product-documentation provider (Confluence / PDF / URL fetch).* Deferred — start with
  files-in-plugin (`skills/`) + ticket links, which already exist.
- *Require source and mock it.* Rejected — defeats the purpose; some products genuinely cannot expose
  source.
- *Make docs mandatory for sourceless mode.* Rejected — docs are often partial/absent per ticket;
  best-effort degradation is required (R8).
- *Degrade / disable the source-citing lenses in sourceless mode (rely on `r-diagnosis` + `r-fidelity` +
  the human) instead of retargeting citations to a ticket/doc snapshot.* Cheaper, but drops the
  deterministic anti-fabrication check. **Recommended: retarget (R13)** — this is the one open
  sub-decision for the maintainer.

## Phasing

Shipped in two phases so the usable core lands without the heaviest part.

- **Phase A (this iteration) — sourceless mode, honest diagnosis.** R0–R11, R14; the *(Phase A)* half of
  R12 (`diagnostics.py` → `INDETERMINATE`; source-citing lenses **degrade explicitly**, no `source:line`);
  the two ingestion gaps; a sourceless demo SUT green in CI; docs + CHANGELOG. Acceptance criteria
  AC0–AC11 + AC14.
- **Phase B (follow-up) — retarget the anti-fabrication machinery.** The *(Phase B)* half of R12 (lens
  citations retarget to ticket/doc anchors) + R13 (snapshot the ticket/docs; `citation_gate` +
  `freshness_gate` resolve/verify against it). Acceptance criteria AC12–AC13.

Source-backed SUTs are unchanged in both phases (R0).

## Executive Summary

_(Populate before opening the PR.)_
