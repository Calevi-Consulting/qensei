# Contributing to Qensei

Thanks for your interest in contributing. Qensei is a backend-aware QA framework
driven by an AI coding assistant.

Qensei is young. The engine, the review lenses (`agents/`), and the policies can
be wrong — especially at edge cases and in critical paths. Fixes to any of it are
welcome, not just new plugins, and so are challenges to the rules themselves (open
a Discussion or an issue). Treat this guide as a starting point, not a barrier.

## Ground rules

- **Fork and branch.** Fork the repo, branch off `main`, and open a pull request
  from your fork. `main` goes through the same PR + gate for everyone.
- **Prefer focused PRs.** Smaller, single-purpose changes are easier to review and
  to revert. Try not to reformat or refactor code you did not need to touch — but
  this is a guideline, not a tripwire.
- **The gate decides "green".** The `engine/` runtime is plain Python 3 stdlib and
  runs with no AI in the loop. A PR is mergeable when the `qa-gate` workflow passes.

## Development setup

The runtime is zero-dependency (pure stdlib) — `make demo` / `make test` /
`make design` need no install. The dev/test toolchain (pytest, ruff, pip-audit,
Playwright) is Poetry-managed:

```bash
make install      # provision the dev toolchain into ./.venv (run once)
make verify       # full local CI: lint + cve + pytest + fidelity + secrets
make check        # faster offline pre-commit ritual
```

Run `make verify` (or at least `make check`) before pushing — it mirrors what CI
enforces in `.github/workflows/qa-gate.yml`.

## Ways to contribute

Two paths, both welcome:

- **Add a product under test** — the most self-contained path. A product is a
  plugin under `sut/<name>/`, and adding one needs *no* changes to the core. See
  `sut/contract.md` for the manifest keys and `plugin.py` hooks, and
  `sut/mock-shop/` as the reference site. Keep one regression case per
  `packs/<id>/` directory so concurrent edits do not collide.

- **Fix or improve the core** — the engine (`engine/`), the review lenses
  (`agents/`), and the governance (`policies/`) are all fair game. The framework is
  young; if a lens misfires, a rule is wrong, or the engine has a bug, a PR is very
  welcome — open an issue first if you would like to discuss the approach. The one
  architectural constraint that stays: keep `engine/` and `policies/`
  **product-neutral** — do not hardcode any single SUT's endpoints, rules, or
  skills into them.

## Commit messages

- Conventional prefixes: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`.
- Imperative mood, atomic commits.
- **No AI-attribution.** Do not add `Co-Authored-By` trailers naming an assistant,
  nor "Generated with…" footers.

## The prime invariant (and its escape valve)

The one hard line: **do not _silently_ weaken a spec just to turn a red gate
green.** That single failure mode is what the whole framework exists to prevent.
`engine/fidelity_lint.py` (a pre-commit hook and a CI step) flags weakenings —
a removed case, a weakened persona, shrunk `tags` / `requires` / `covers`, a
downgraded severity, dropped assertions, or an added skip/xfail on a changed pack.

But a flag is a **conversation, not a veto.** If you believe a case, an assertion,
a lens, or a rule is genuinely *wrong* — and in a young framework some will be —
correcting it is a legitimate and welcome contribution. When that is what you are
doing:

- Say so explicitly in the PR: what was wrong, and why the change is a correction
  rather than a workaround.
- Run the lint with `--allow-reshape` to downgrade intentional-refactor findings to
  warnings.
- A human reviews the reshape. The gate raises the floor; it does not have the
  final word.

The distinction the gate cares about is *cheating* a red gate (bad) versus *fixing*
a wrong spec or lens with justification (good). When a case fails and you are not
sure which it is, `engine/diagnostics.py` and the review panel help classify it — a
`TEST_BUG` means fix the test; a `REAL_BUG` means keep the test red and file a bug.

## Where to start

- `README.md` and `docs/overview.md` — entry points.
- `docs/walkthrough.md` — the end-to-end journey on `SHOP-456`.
- `CLAUDE.md` — architecture and commands.
- Issues labeled **`good first issue`**, or ask in **Discussions** if anything is
  unclear.
