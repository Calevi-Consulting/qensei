# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **A seeded gate red now declares itself** ([#41](https://github.com/Calevi-Consulting/qensei/issues/41)).
  `--seed-bug` is a flag on the gate binary, and nothing recorded it: a seeded run produced exit 1, a
  failing `<testcase>` and a report byte-indistinguishable from a genuine regression, on any SUT. The gate
  now announces a seeded run on stderr and stamps every report with `qensei.seeded` (JUnit `<property>`) /
  `seeded` (JSON) — emitted on **every** report, `false` included, so an absent marker is never ambiguous.
  `--seed-bug` reaches only an `in_process` factory; requested against a `remote` runtime it is dropped, and
  the gate now says so and stamps the run unseeded rather than claiming a seeding that did not happen
  (`SUTConnector.seeded`). `policies/communication-standards.md` gains the matching evidence rule: a
  gate-state claim carries the invocation that produced it. Surfaced by the review-panel orchestrator on its
  first real run.

### Added

- **Design panel + non-discretionary panel tiers** (`specs/005-design-panel-and-invocation-tiers.md`,
  WS-A/B/C): a new design-stage lens, **`r-design`**, reviews the (spec, plan) pair at `/automate` Phase 2b
  before any pack code exists, with its findings recorded per-finding in the plan
  (`F<n> APPLIED|REJECTED|FLAGGED|DEFERRED`) and gated by `engine/design_panel_lint.py`. Phase-4 panel
  invocation is now **tiered** (R-DIAGNOSIS as a subagent on every non-green result; the full panel on
  flags / `REAL_BUG` / 2nd cycle / reshape ack / a pack's first landing) and **recorded** in every
  validation report (`### Panel`), gated by `engine/panel_section_lint.py`. A read-only **ORIENT** step
  now precedes every lens, returning the record (`rejected_fixes`, `contradicts_subject`,
  `prior_attempts`). Both lints are stdlib, wired in pre-commit, `make check` and CI (changed files only).
- **Deterministic review-panel orchestrator** (spec 005 WS-D/E): `workflows/review-panel.js` implements the
  panel protocol as a Workflow-tool script over the same `agents/` lenses and the same `engine/` gates —
  ORIENT → `engine.diagnostics` → R-DIAGNOSIS → flagged R-EVIDENCE / R-MECHANISM in parallel →
  `engine.citation_gate` → JUDGE — with a subject gate that throws rather than convening a panel against a
  null subject. `scripts/install.sh` wires `.claude/workflows`. The model-driven path stays the always-on
  default; the orchestrator is human-triggered. `docs/multiagent/execution-architecture.md` documents the
  timeline: the three laws, every dispatch condition, the lens-or-lint decision and its graduation path.
- **Sourceless SUT mode** (`specs/002-sourceless-ticket-driven-mode.md`): a SUT can declare no backend
  source (omit `source`, or `{"source": {"mode": "none"}}`) and still run the regression gate against its
  live runtime. `design` falls back to the ticket + docs, `diagnostics` returns `INDETERMINATE` (contract
  of record = the ticket), the source-freshness gate is a no-op, and the source-citing review lenses cite
  the ticket/doc snapshot (see below). Source-backed SUTs are unchanged. Reference SUT: `sut/widget-api`.
- **Ticket comments as an input.** The normalized ticket gains `comments[]`; `/automate` reads the
  discussion (scope refinements, edge cases) and accepts a ticket validated **outside** Qensei — no prior
  `/validate` run required.
- **Sourceless anti-fabrication (Phase B).** The review lenses now cite the **ticket/doc snapshot** —
  `citation_gate` resolves `sut/<name>/{tickets,skills,learnings,specs}/<file>:<line>` against the committed
  in-repo ticket + docs — instead of degrading, restoring the deterministic anti-fabrication floor against
  the ticket; `freshness_gate` treats that snapshot as always-current.

## [0.1.0] - 2026-07-03

Initial public release.

### Added

- **Deterministic engine** (`engine/`, pure Python 3 stdlib) — the regression
  gate (`make test`) as the single source of truth for "green", with a
  false-green guard (empty / all-skipped / unreachable SUT exits non-zero).
- **SUT plugin seam** (`sut/<name>/`) — a product under test is a self-contained
  plugin (manifest, optional hooks, source, packs, ui-packs, specs). Reference
  sites: `mock-shop` and `restful-booker` (live auth + a Playwright UI lane).
- **Three capabilities over one backend connection** (`SUTConnector`): design
  (coverage gaps from the backend source), regress (the gate), and diagnose
  (`REAL_BUG` vs `TEST_BUG` against `BUSINESS_RULES`).
- **AI-assistant legs** — slash commands (`/validate`, `/automate`,
  `/report-bug`) and an advisory, read-only review panel (`agents/`).
- **Prime-invariant forcing functions** — `fidelity_lint`, `citation_gate`,
  `freshness_gate`, and secrets scanning, wired as pre-commit hooks and CI.
- **CI** — `qa-gate` GitHub Actions workflow: lint + CVE scan + framework tests +
  fidelity, and the per-site integration and UI gates.
- **Project governance** — `CONTRIBUTING.md`, `CODEOWNERS`, a PR template,
  `SECURITY.md`, `CODE_OF_CONDUCT.md`, and issue templates.

[Unreleased]: https://github.com/Calevi-Consulting/qensei/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Calevi-Consulting/qensei/releases/tag/v0.1.0
