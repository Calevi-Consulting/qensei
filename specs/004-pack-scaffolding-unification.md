# Spec 004 — Unify pack scaffolding (mechanical + AI) and add the UI-pack template

> **Tracking**: [Calevi-Consulting/qensei#34](https://github.com/Calevi-Consulting/qensei/issues/34).
> Consistent with the existing top-level tooling specs (001–003), the filename stays numbered/ticketless.
> **Ownership**: internal — this touches authoring tooling and the pack-structure conventions adjacent to
> `engine/`, so it carries an internal assignee and is **not** a good-first-issue (per-SUT packs remain
> fine for external collaborators).

## Status: COMPLETE

Both phases implemented: Phase A (the `--ui` scaffolder + shared templates + tests + docs) and Phase B
(`commands/automate.md` Phase 3 now invokes the scaffolder for file creation). All acceptance criteria
below are met.

## Context

There are two ways to author a regression pack, and they currently **duplicate** the definition of
"what a pack is" rather than sharing it:

- **Mechanical** — `make new-pack` (`scripts/new_pack.py`) emits a skeleton from string templates:
  `packs/<TICKET>-<SLUG>/case.py` (a `RegressionCase`), `README.md`, and a `specs/<id>.md` stub. It is
  zero-dependency, no-AI, deterministic, performs an atomic claim (refuses to overwrite), validates the
  ticket/slug, and produces an immediately auto-discoverable pack.
- **AI-assisted** — `/automate` (`commands/automate.md`) reads the ticket + SUT source/skills and writes
  the spec and the pack **directly**, describing the file layout in prose (Phase 2 / Phase 3). It does
  **not** reference `new_pack.py` or `make new-pack`.

Two independent encodings of the same structure is a drift hazard. The drift has already manifested:

1. **The mechanical scaffolder is REST-only.** `new_pack.py` emits a `RegressionCase` into `packs/`; there
   is no `UICase` / `ui-packs/` template and no Make target for one. A QA authoring a UI pack must
   hand-copy a sibling pack.
2. **This copy-paste is the documented root cause of the BOOK-UI-2 defect (PR #26).** The new UI case
   began as a copy of `BOOK-UI-1`, which is why its `run()` initially ran the happy-path booking and its
   `covers` listed `POST /booking/` — an endpoint the validation scenario never exercises. The absence of
   a UI scaffolder made hand-copying the only path.

This spec proposes closing the gap (a UI-pack template) and removing the duplication (one canonical
source of pack structure, consumed by both frontends), while preserving the mechanical path's defining
properties.

## Requirements

- **R1 — Single source of truth for pack structure.** The `case.py` / `README.md` / spec-stub templates
  for each pack kind (REST, UI) live in exactly one place, consumed by every authoring frontend. No
  frontend re-specifies the skeleton independently.
- **R2 — UI-pack scaffolding.** `new_pack.py` gains a UI mode that emits a `UICase` skeleton into
  `ui-packs/<TICKET>-<SLUG>/` (`case.py` with `run(self, page, base_url, expect)` + `README.md`) plus the
  `specs/<id>.md` stub, with the same atomic-claim, validation, and auto-discovery guarantees as the REST
  mode. A discoverable Make target exposes it.
- **R3 — `/automate` builds on the scaffolder.** `/automate`'s file-creation step invokes the mechanical
  scaffolder (rather than describing the layout in prose), then fills the generated skeleton with the real
  spec content and test logic. The prose no longer re-specifies the file skeleton.
- **R4 — Preserve the mechanical path's properties.** The mechanical path remains zero-dependency (pure
  stdlib), no-AI, deterministic, offline-capable, atomic (refuse-overwrite), naming-validated, and its
  output is auto-discovered by the runner / UI bridge. No runtime dependency is introduced.
- **R5 — Structure templates do not enter `engine/`.** `engine/` is the AI-free deterministic gate;
  authoring tooling is a separate concern. The shared templates live under `scripts/` (or a `tools/`
  templates module), never in `engine/`.
- **R6 — Skeletons are honest, not false-green.** A freshly scaffolded pack must be collectable but must
  not pass as a real assertion (its `run()` body is an explicit, obviously-incomplete TODO, matching the
  current REST template's placeholder), so a reviewer or the fidelity/coverage lenses can tell a skeleton
  from a finished pack.

## Acceptance Criteria

- [x] `python3 scripts/new_pack.py --sut sut/restful-booker --ui BOOK-9 cancel-flow` creates
  `sut/restful-booker/ui-packs/BOOK-9-cancel-flow/case.py` (a `UICase` subclass with
  `run(self, page, base_url, expect)`), `.../README.md`, and `sut/restful-booker/specs/BOOK-9-cancel-flow.md`
  (stub, only if absent).
- [x] The UI mode refuses to overwrite an existing `ui-packs/<id>/` (atomic claim), mirroring the REST mode.
- [x] The REST path (`new_pack.py` without `--ui`) is byte-for-byte unchanged versus its pre-change output
  (guarded by a golden-output test), and all existing engine/tooling tests remain green.
- [x] The `case.py` / `README.md` / spec-stub templates for both kinds exist in exactly one module,
  imported/consumed by `new_pack.py` for both modes; no second copy of the skeleton remains in the codebase.
- [x] `commands/automate.md` Phase 3 invokes the scaffolder (`make new-pack` / `new_pack.py`, with `--ui`
  for the UI fallback) for file creation, and its prose no longer independently describes the pack skeleton.
- [x] A `make new-ui-pack SUT=... TICKET=... SLUG=...` target exists and appears in `make help`.
- [x] The generated `UICase` skeleton's `run()` is an explicit TODO placeholder (not a passing assertion),
  so an un-filled skeleton does not merge as a false-green pack.
- [x] `scripts/new_pack.py` self-documents the UI mode: its module docstring carries a `--ui` usage
  example (alongside the existing REST examples) showing the resulting `ui-packs/<id>/` + `specs/<id>.md`
  paths, and the `--ui` argparse argument has `help=` text — so `python3 scripts/new_pack.py --help` and the
  file header describe the UI mode without relying on external docs.
- [x] Docs updated: the "Scaffolding" line in `CLAUDE.md` and the pack-authoring section of
  `sut/contract.md` mention the UI scaffolder.

### Integration-boundary AC

- [x] A scaffolded UI pack is **discovered and collected by the real Playwright UI bridge**: after
  `python3 scripts/new_pack.py --sut sut/restful-booker --ui <id> <slug>`, the pack appears as a
  parametrized case under `tests/test_ui.py` (e.g. collection lists `restful-booker::<ID>`), exercising the
  actual `discover_ui_cases` → `ui_packs_dir` discovery path — not a mocked file check. (Scaffolding writes
  files; the load-bearing contract is that the framework then *finds and runs* them, so at least one AC must
  exercise that downstream discovery.)

## Risks & Assumptions

- **Template extraction could silently change REST output.** Mitigation: a golden-output test asserts
  `make new-pack` produces identical bytes before/after the refactor (AC above); the change is a pure move,
  not a rewrite.
- **`/automate` coupling to the scaffolder CLI.** Rewiring Phase 3 to shell out couples the command to the
  script's CLI surface. Mitigation: keep the `new_pack.py` CLI stable and covered by a test; the shell-out
  is a documented, single call.
- **False-green skeletons.** A UI skeleton that accidentally asserts something true would merge green. R6 /
  the TODO-placeholder AC mitigate this; the fidelity and coverage lenses remain the backstop.
- **Assumption:** templates belong in `scripts/`/`tools/`, not `engine/` (R5) — `engine/` must stay the
  AI-free gate with no authoring concerns.
- **No runtime dependency** is added; the mechanical path stays pure stdlib (consistent with the framework's
  zero-dependency runtime rule).
- **Rollback:** revert the commit. The change is additive (new `--ui` flag, new `make new-ui-pack` target,
  new shared-templates module); the existing `make new-pack` REST behavior is preserved, so there is no
  breaking removal to undo.

## Alternatives Considered

- **Drop the mechanical path; author packs AI-only via `/automate`.** Rejected. It makes the AI assistant a
  hard dependency for a core authoring flow, contradicting the framework's defining split (a deterministic
  core that runs with no AI in the loop, with AI-driven legs *around* it — the same posture as the
  zero-dependency `make test` / `make design`). It also loses determinism, offline/air-gapped use,
  no-cost/instant scaffolding, and unit-testability of "what a pack is."
- **Keep both paths duplicated as-is.** Rejected. The duplication already produced observable drift (the
  UI-scaffolding gap → the PR #26 copy-paste defect); leaving it invites recurrence.
- **Put the shared templates in `engine/`.** Rejected per R5 — `engine/` is the no-AI gate; authoring
  tooling does not belong in the single source of truth for "green."

## Phasing

- **Phase A (mechanical, self-contained, ships alone):** extract the shared template module; add `--ui` to
  `new_pack.py`; add the `make new-ui-pack` target; add the golden-output test and the discovery
  integration-boundary test; update `CLAUDE.md` / `sut/contract.md`. This closes the PR #26 gap on its own.
- **Phase B (convergence):** rewire `/automate` Phase 3 to invoke the scaffolder for file creation and
  strip the duplicated skeleton prose from `commands/automate.md`.

Phase A delivers immediate value (a UI scaffolder) without touching `/automate`; Phase B removes the
duplication once Phase A establishes the single source of truth.

## Executive Summary

Establishes one canonical source of pack structure and closes the UI-scaffolding gap behind the #26
copy-paste defect. **Phase A** adds a UI mode to the mechanical scaffolder (`make new-ui-pack` /
`new_pack.py --ui`) that emits a `UICase` skeleton into `ui-packs/` with the REST mode's atomic-claim,
naming-validation, and auto-discovery guarantees — plus a golden guard keeping REST output byte-identical
and an honest (failing-TODO) skeleton that cannot merge as a false green. **Phase B** rewires `/automate`
Phase 3 to invoke the scaffolder for file creation instead of re-describing the layout, so pack structure
has a single source of truth. The mechanical path stays zero-dependency, no-AI, and deterministic; the
change is additive and revert-to-undo. Reviewers should look first at `scripts/new_pack.py` (REST
templates untouched; `--ui` routing) and `tools/tests/test_new_pack.py` (including the integration-boundary
discovery test).
