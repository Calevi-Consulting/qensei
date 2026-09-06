# Validation Report — spec 005 PR 1: design panel (R-DESIGN), invocation tiers, ORIENT

**Date:** 2026-09-06
**Spec:** `specs/005-design-panel-and-invocation-tiers.md` — WS-A, WS-B, WS-C + integration-boundary AC 1 and 2 (WS-D/E and integration AC 3 land in PR 2; Status stays INCOMPLETE)
**Branch:** `feat/005-design-panel-and-tiers`
**Scope:** a design-stage lens at `/automate` Phase 2b with a per-finding record gated by a lint; Phase-4 panel invocation made tiered and recorded; an ORIENT step before any lens reasons.

## What changed

- **Two record gates in `engine/`** (pure stdlib, same home and contract as `fidelity_lint` / `coverage_lint`):
  `engine/design_panel_lint.py` (a touched `sut/<name>/plans/*.md` must carry `## Design panel` with
  `- ran: N findings` + one `- F<n> APPLIED|REJECTED|FLAGGED|DEFERRED: <reason>` line per finding, labels
  `F1..FN` each exactly once, or `- waived: <reason>`) and `engine/panel_section_lint.py` (a touched
  validation report must carry `### Panel` with `ran:` / `waived:`; `TEMPLATE.md` excluded by name). Both gate
  presence, never verdict. Wired in `.pre-commit-config.yaml`, `make design-panel` / `make panel-record`
  (inside `make check`, diff vs `HEAD`), and the CI `checks` job (diff vs the base ref). `tools/tests/`: +35
  unittest pins (all polarities, the ownership wording in the failure message, the real-plan pin).
- **`agents/r-design.md`** — the design-stage lens: freshness self-gate, ten product-neutral checklist items,
  ≤6 ranked findings `F1..Fn` with severity + citation-or-`hypothesis:` + one alternative, `needs_mechanism` /
  `needs_evidence`, and the hard limit that it never writes a disposition. `docs/multiagent/r-design.md` in the
  per-lens doc shape (BOOK-UI-2 / PR #26 as this repo's own case).
- **Protocol:** `docs/multiagent/review-panel.md` gains *Invocation tiers* (Tier 1 always / Tier 2 triggers /
  the record row, with the under-invocation case study) and the *ORIENT* step (⓪′, between the freshness gate
  and R-DIAGNOSIS; seven output fields; not a lens). Verdict vocabulary aligned with `judge.md` /
  `diagnostics.py` (`ENV_OR_TRANSIENT` / `INDETERMINATE`). `commands/automate.md` Phase 2b (design panel,
  tiered, record, who owns dispositions, no JUDGE at 2b) and Phase 4b (ORIENT → deterministic lens →
  R-DIAGNOSIS as a subagent; Tier-2 triggers; record). `agents/judge.md` consumes the ORIENT record.
- **Registries/docs:** `agents/README.md`, `docs/multiagent/README.md`, `docs/diagnostics-and-review-panel.md`,
  `docs/quality-gates.md`, `CLAUDE.md`, the generated `.claude/CLAUDE.md` (`scripts/install.sh`),
  `validation-reports/TEMPLATE.md`, `CHANGELOG.md`.
- **Demonstrator:** `sut/mock-shop/plans/2026-09-06-shop-456-bulk-discount.md` — a retro-plan for the
  already-automated SHOP-456 pack, reviewed by R-DESIGN for real (below), carrying the first `## Design panel`
  record in the repo.

## The demonstrator — R-DESIGN, run for real (integration-boundary AC 1)

Three read-only subagent dispatches over the (spec, plan) pair; `git status` before and after each run was
byte-identical (no lens wrote anything). Every `file:line` the lenses cited was pushed through
`engine/citation_gate.py`: **26 + 23 + 5 citations, all resolve, exit 0**. Spot-checked by hand:
`app.py:137` (`sum(...)`), `:139` (`>=`), `:150` (`state["cart"] = []`), `:159` (server-global `state`),
`tickets/SHOP-456.md:37` ("3 or more"), `tests/conftest.py:43-55` (per-worker boot).

| Run | Dispatch | Tools reported | Findings | Flags |
|---|---|---|---|---|
| 1 | `general-purpose` carrying `agents/r-design.md` verbatim | (full toolset — not enforced) | F1 FIX · F2 FIX · F3 FIX · F4 FIX | `needs_mechanism` true · `needs_evidence` false |
| 2 (Tier 2) | `r-mechanism` (registered) | read-only | 7/7 mechanism claims **CITED**; 13 mechanism calls surfaced | — |
| 3 | `r-design` (registered) | **Read, Bash — no Write/Edit** | F1 FIX · F2 FIX · F3 FLAG · F4 FLAG | `needs_mechanism` true · `needs_evidence` false |

**Why run 1 was not under the lens's own name.** A lens file added to `.claude/agents` mid-session is not
registered as an agent type until the wiring is reloaded (the caveat `agents/README.md` § Notes already
documents; the dispatch returned `Agent type 'r-design' not found`). After `make install` regenerated the
wiring the type appeared, and run 3 confirms the `.claude/agents → subagent` leg with the read-only allowlist
applied. Run 1's findings are the ones recorded in the plan (verified first); run 3 is the consistency sample.

**Consistency between the two R-DESIGN runs — 4/4 findings overlap in substance:**
run-1 F1 ≡ run-3 F1 (ticket says "3 *or more*" summed across lines; the spec pins one qty=3 line — a
`>=`→`==` at `app.py:139` or `sum`→`max` at `:137` passes unseen); F2 ≡ F2 (the AC's identity
`total = subtotal − discount` is asserted as literals; the case never reads `subtotal`; the plan misdescribed
it); run-1 F4 ≡ run-3 F3 (parallel safety attributed to `isolate`, which runs *before* a case; the cart is
server-global and SHOP-123 mutates it too; the real mechanism is one server per xdist worker); run-1 F3 ≈
run-3 F4 (setup writes — the add, and checkout's clear — are trusted unchecked, so a setup break would be
routed to `REAL_BUG` labelled `bulk-discount`). Two severities differ by one step (FIX vs FLAG). Run 3 added
one citation run 1 lacked (`skills/SHOP.md:23-24`, the gotcha that names the cross-line sum). Nothing was
proposed that weakens a criterion; both runs said so explicitly.

**What R-MECHANISM added beyond confirmation:** `engine/diagnostics.py:89-94` compares only `rate` —
`min_qty` is carried in the claim but never compared — and the verdict's `rule` label is claim-derived, not a
fault localisation (`diagnostics.py:80-119`). The plan overstated the first; corrected. Both are
framework-shape observations about the deterministic lens, surfaced here for a human, not changed in this PR.

**Dispositions** (the GENERATOR's proposal, recorded in the plan for the human to ratify at the approval
gate): F1 **DEFERRED** (a valid spec gap; closing it amends a human-approved spec + extends the case — a
SHOP-456 follow-up), F2 / F3 / F4 **APPLIED** to the plan text (mapping rows state what is asserted; the
checkout-clear dependency named as an unchecked precondition with its attribution consequence; runtime
expectations name the shared object and the real isolation mechanism). Case-level hardening from F2/F3 is
folded into the F1 follow-up. `make design-panel` → `design-panel lint: clean` on the real record.

**Lens lifecycle signal:** F2 (plan faithfulness to the case) and F3/F4 (unchecked setup writes) recurred
across runs — candidates to graduate into lints per the r-design doc's "honest limit".

## Pre-merge re-verification (adversarial, on request)

Four hypotheses probed empirically against the first version of the lints — three held, and were fixed
before merge. All three belong to the vacuous-pass family the source framework had already paid for once
(its scaffolded plan illustrated the record format in an HTML comment and handed every new pack a pass).

| # | Hypothesis | Result | Fix |
|---|---|---|---|
| H1 | A report copied verbatim from `TEMPLATE.md` satisfies the lint | **confirmed** — `check_text(TEMPLATE) is None` | an unfilled `<placeholder>` is not an entry; HTML comments stripped before matching; pinned by a test that reads the real template |
| H2 | A **new, untracked** plan is invisible to `make check` | **confirmed** — `git diff HEAD` lists no untracked files; the first plan of a pack (the common case) skipped the offline ritual; only pre-commit would have caught it | `make design-panel` / `make panel-record` union `git diff --name-only HEAD` with `git ls-files --others --exclude-standard` |
| H3 | A `ran:` line (or `F<n>` disposition) anywhere in the file counts | **confirmed** | entries and dispositions count only inside the section (header → next markdown header) |
| H4 | CI actually ran the lints over the new plan and report | OK — the `checks` job log shows `design-panel lint: clean` / `panel-record lint: clean` with the files passed | — |

Also stated where it was only implied: the `ran:` count is R-DESIGN's; a Tier-2 lens's output folds into
the `F<n>` line it bears on. +10 test pins (44 across the two lint modules). Design decisions re-examined
and kept: no JUDGE at 2b; the GENERATOR proposes / the human ratifies; changed-files-only scope; F1
DEFERRED on the demonstrator (amending a human-approved spec is the human's call).

## Phase 3 — Tests

| Check | Command | Result |
|---|---|---|
| Engine + gate units | `make test-engine` | **128 passed** (was 80; +48 lint pins incl. the real-plan and real-template pins) |
| Regression gate (offline ritual) | `make check` | OK — fidelity, coverage-lint, **design-panel: clean**, **panel-record: clean**, lint, secrets |
| Full local CI | `make verify` | OK — ruff, pip-audit, pytest 87 passed, fidelity, coverage-lint, secrets |
| Hook path, negative polarity (integration AC 2) | scratch plan + scratch report, `git add -N`, `make check` | **fails** naming `[DESIGN-PANEL-RECORD-MISSING]`; `make panel-record` names `[PANEL-SECTION-MISSING]` |
| Hook path, positive polarity | same files with the records added | `design-panel lint: clean` · `panel-record lint: clean` |
| Citations in the demonstrator plan | `python3 -m engine.citation_gate sut/mock-shop/plans/…` | 5 citations, all resolve |
| Lens citations | `engine.citation_gate` over runs 1 / 2 / 3 | 26 / 23 / 5, all resolve |

## Phase 4 — Code quality

- The two lints are near-twins by design and deliberately **not** shared: they gate different artifacts at
  different phases, and coupling them would mean neither could change shape alone (the count/label
  reconciliation exists only on the design-panel side).
- No dead code; ruff clean over the whole tree; no runtime dependency added (`engine/` stays stdlib).

## Phase 5 — Security

- `pip-audit 2.10.1`: no known vulnerabilities. `make secrets`: clean; inline scan of the diff: no
  credentials, no keys, no URLs with embedded auth.
- OWASP over the changed code: the lints are regex checks over local text files — no subprocess, no eval,
  no deserialisation, no network. Paths come from pre-commit / `git diff` / CI, never from untrusted input.
- Supply-chain / agent-config awareness (advisory): `.github/workflows/qa-gate.yml` gains two diff-scoped
  `python3 -m engine.<lint>` steps (no new actions, no new deps); `CLAUDE.md` gains doc lines only; a new
  agent file `agents/r-design.md` is read-only by frontmatter (`disallowedTools: Write, Edit, …`) — run 3
  above confirms the allowlist is applied when loaded at session start.

## Phase 5.5 — Release safety

- **Rollback:** revert the PR. Everything is additive — new files (2 lints, 2 tests, 1 lens, 1 doc, 1 plan,
  this report), plus hook / Make / CI entries and doc paragraphs. The lens is advisory: nothing downstream
  depends on it. Changed-files-only scope means no existing plan or report is retro-gated.

### Panel

- ran: R-DESIGN at Phase 2b on the demonstrator — 4 findings (F1 DEFERRED, F2-F4 APPLIED, recorded in `sut/mock-shop/plans/2026-09-06-shop-456-bulk-discount.md`), Tier 2 R-MECHANISM 7/7 CITED, all citations resolve; consistency re-run under the registered `r-design` type 4/4 overlap.
- waived (Phase 4): no non-green gate result this cycle — the change is lints, docs and a plan; the regression gate was green throughout.

## Result

Offline checks green (`make check`, `make verify`); CI to run on the PR. Spec 005 WS-A/B/C and integration AC
1-2 checked; WS-D/E and integration AC 3 remain open for PR 2 — Status stays INCOMPLETE by design.
