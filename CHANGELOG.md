# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
