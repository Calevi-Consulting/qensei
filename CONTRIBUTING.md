# Contributing to Qensei

Thanks for your interest in contributing. Qensei is a backend-aware QA framework
driven by an AI coding assistant. This guide covers how to propose a change.

## Ground rules

- **Fork and branch.** Fork the repo, branch off `main`, and open a pull request
  from your fork. Do not commit directly to `main`.
- **One focused change per PR.** Keep changes surgical — edit only what the change
  requires. Do not reformat or refactor adjacent code you did not need to touch.
- **The gate is the source of truth for "green".** The `engine/` runtime is plain
  Python 3 stdlib and runs with no AI in the loop. A PR is mergeable only when the
  `qa-gate` workflow passes.

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

## Adding a product under test

A product under test is a plugin under `sut/<name>/`. Adding a product means
writing a plugin — never editing `engine/` or `policies/`, which must stay
product-neutral. See `sut/contract.md` for the manifest keys and `plugin.py`
hooks, and `sut/mock-shop/` as the reference site.

Keep one regression case per `packs/<id>/` directory so concurrent edits do not
collide.

## Commit messages

- Conventional prefixes: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`.
- Imperative mood, atomic commits.
- **No AI-attribution.** Do not add `Co-Authored-By` trailers naming an assistant,
  nor "Generated with…" footers.

## The prime invariant

Never quietly weaken a spec to turn a red gate green. This is enforced by
`engine/fidelity_lint.py` (a pre-commit hook and a CI step): removing cases,
weakening a persona, shrinking `tags` / `requires` / `covers`, downgrading
severity, dropping assertions, or adding a skip/xfail on a changed pack fails the
gate. When a case fails, classify it — a `TEST_BUG` means fix the test; a
`REAL_BUG` means keep the test red and file a bug — rather than softening the
assertion.

## Where to start

- `README.md` and `docs/overview.md` — entry points.
- `docs/walkthrough.md` — the end-to-end journey on `SHOP-456`.
- `CLAUDE.md` — architecture and commands.
