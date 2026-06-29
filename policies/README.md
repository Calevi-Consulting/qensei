# QA Framework Policies

These are general, QA-applicable development policies that govern any project built on this
framework. They define the default development practices — spec-driven workflow, test philosophy,
coding standards, security review, and release safety — for manual test design, automated
regression, and diagnostics work against any system under test.

Each policy is the default; a project may extend or relax it via its own project-level config.

## Policy index

| File | What it governs |
|------|-----------------|
| [`methodology.md`](methodology.md) | Core spec-driven QA methodology: the 0-to-8 implementation phases (Orient, Select, Implement, Validate, Code-Quality, Security, Release-Safety, Record, Reconcile, Commit, Signal), spec conventions (intent contract + testable acceptance criteria + non-skippable reconciliation gate), and the humans-own-intent / AI-owns-implementation ownership model. |
| [`testing-philosophy.md`](testing-philosophy.md) | Tests as behavioral contracts rather than coverage targets: avoid mock-the-universe isolation, and require at least one real-downstream-system (integration/e2e) acceptance criterion whenever a scenario crosses an integration boundary. |
| [`communication-standards.md`](communication-standards.md) | Authoring standards for durable QA artifacts (specs, test-design docs, validation/diagnostic reports, commit/PR descriptions): factual language, neutral voice, evidence-and-uncertainty disclosure, no fabrication — with a generation-time checklist, BLUF/MECE/SCQA structure, and an AI-vocabulary substitution table. |
| [`security-review.md`](security-review.md) | Mandatory two-part security pass: tool-verified dependency CVE scanning (recorded tool + version, non-skippable) plus an AI-assisted best-effort OWASP Top 10 and anti-pattern review of changed code, with prioritized remediation. |
| [`input-hygiene.md`](input-hygiene.md) | Input/display/log hygiene for AI coding tools: context exclusion, credential display safety (prefer config-based auth, prompt before exposing secrets), and a no-secrets-in-logs rule (mask at the logging boundary, scrub captured artifacts). |
| [`release-safety.md`](release-safety.md) | Reversibility discipline: every change must have a minutes-to-undo rollback path documented in the commit or PR; prefer additive changes and verify rollback before merging when shared test data, framework core, shared-environment state, or CI gating is touched. |
| [`python-standards.md`](python-standards.md) | Python coding standards: style/syntax (3.12+, PEP 8, type hints, Pydantic v2), tooling (pyproject/ruff/pytest), error handling, testing (behavioral contracts, real-collaborator integration tests), and optional data/performance guidance. |
| [`git-workflow.md`](git-workflow.md) | Git conventions: commit message rules (conventional prefixes, imperative mood, atomic commits, ban on AI co-author trailers and AI attribution footers), branch naming, a pre-push remote connectivity check, and force-push safety. |

## What is intentionally excluded

Product- or company-specific policy modules are not part of this generic set — they are
domain-plugin concerns, not framework concerns. Examples excluded by design:

- platform-specific git workflows
- integration specifics for a particular Jira / GitLab / secrets backend
- cluster-inspection or other infrastructure tooling

## Domain plugins

Domain plugins under `sut/` may add their own policies on top of this set.
