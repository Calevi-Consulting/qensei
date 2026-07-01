# 001 — SUT source provisioning (local clone of each SUT's real source)

> **Note**: This work has no associated issue tracker ticket. Consider creating one for traceability.

## Context

Qensei's design + diagnostics + review lenses read the backend **SOURCE** (`ROUTES` /
`BUSINESS_RULES`, plus the code lenses cite) from `manifest.source.path`. Today that path is
only ever a **local directory that must already exist**: for the two example SUTs it holds a
committed in-repo mock; for a real backend the manifest note says it "would point at a
checked-out clone of the GitHub source" — but **nothing in the framework materialises that
clone**. There is no `source.repo` field and no clone/refresh step (`git clone` /
`source_url` appears nowhere in the engine, Makefile, or scripts). `engine/freshness_gate.py`
only *checks* an existing clone (`HEAD == origin/HEAD`); `engine/citation_gate.py` reports a
remote plugin with no clone as `UNVERIFIABLE`. So a real SUT cannot be designed/diagnosed
against current source out of the box.

The intended pattern is a gitignored local clone of the real source, refreshed on demand.
This spec brings that to Qensei — per-SUT and product-neutral — so the local source can be
kept current whenever we design, diagnose a failure, or implement automated tests against a
real backend.

## Requirements

- Extend the `manifest.source` contract with optional `repo` (git URL), `ref`
  (branch|tag|sha), and `depth` (shallow depth; `0`/absent-full = full) fields.
- A product-neutral provisioning tool clones `source.repo` into `source.path` and, on
  re-run, refreshes it to `ref` (idempotent). No-op when `source.repo` is absent (in-repo
  source). Refuses to clobber a non-empty, non-clone `source.path`.
- Correctly distinguish "`source.path` is its own git clone" from "`source.path` lives inside
  the parent Qensei repo" — the tool must never fetch/reset the parent repo.
- A `make sync-source SUT=...` target runs it; it composes with the existing freshness gate.
- The provisioning is an **assistant-driven, network-touching** step (design / diagnose /
  automate flows), never part of the offline deterministic gate (`make test` stays offline).
- Provisioned clones are gitignored; committed in-repo mocks are unaffected.

## Acceptance Criteria

- [x] `sut/contract.md` documents `source.repo` / `source.ref` / `source.depth` and the
      "in-repo source **or** provisioned clone" rule; the adding-a-SUT steps mention it.
      (`sut/contract.md` manifest table + "Adding a new SUT" step 2.)
- [x] `engine/source_sync.py` exposes `sync(sut_dir) -> (status, detail)` returning
      `SKIP` (no `repo`), `SYNCED` (cloned/updated), or `ERROR` (refused/failed), and a
      `python -m engine.source_sync --sut <dir>` CLI that exits non-zero on `ERROR`.
- [x] `make sync-source SUT=sut/<name>` invokes it; no-ops (`SKIP`) for the example SUTs
      (mock-shop, restful-booker) because they declare no `source.repo`. (Verified: both SKIP, exit 0.)
- [x] The tool refuses (`ERROR`, non-zero) to overwrite a `source.path` that exists, is
      non-empty, and is not its own git clone (won't clobber a committed mock/contract).
      (`test_refuses_to_clobber_non_clone_source`; `_is_own_clone` uses `--show-toplevel == path`.)
- [x] **[integration / real downstream]** Against a REAL local `git` origin repo, `sync`
      performs a real `git clone`; after a new upstream commit, a re-`sync` fast-forwards the
      worktree; and `SUTConnector.source_module()` + `engine.design` read the freshly-synced
      `ROUTES` — proving the clone → design/diagnostics path end-to-end, offline, with real git.
      (`TestSyncAgainstRealOrigin.test_clone_then_update_then_read`.)
- [x] `.gitignore` documents/covers provisioned source clones; the example mocks stay tracked.
- [x] `/automate` Phase 0 and `/validate` setup instruct syncing a remote SUT's source before
      reading it (next to the freshness gate).
- [x] `make test-engine` stays green and offline (the integration test uses a local origin,
      no network). (46 tests OK.)
- [x] An opt-in example SUT (`sut/restful-booker-live/`) provisions the REAL upstream source
      and is excluded from the default offline gate + CI matrices (`ALL_SITES` and both CI
      matrices remain `mock-shop` + `restful-booker`). (Verified: `make sync-source` cloned it
      `@ trunk`, `make freshness` FRESH; the clone is gitignored — offline suite unaffected.)

## Risks & Assumptions

- `git` is on PATH (already assumed by `engine/freshness_gate.py`).
- Network is required only for real remote repos; the load-bearing test uses a local `file://`
  origin, so the offline gate is unaffected.
- `ref` is normally a branch/tag; a shallow fetch of an arbitrary sha may be unsupported, so
  the clone path falls back to a full clone + checkout when `--branch <ref>` fails.
- **Reversibility**: additive only — a new module, a new Make target, three optional manifest
  fields, and doc/gitignore edits. No change to existing gate behaviour. Rollback = revert the
  commit; nothing to migrate.

## Alternatives Considered

- A shell `scripts/setup-source.sh`. Rejected: Qensei's engine is stdlib
  Python with `unittest` coverage and already shells `git` from `freshness_gate.py`; a Python
  module is testable the same way and composes with the gate.

## Status: COMPLETE
