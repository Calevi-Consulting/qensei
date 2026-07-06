## What

<!-- One or two sentences: what changed and why. -->

## Context

<!-- Link the ticket or issue, if one exists. -->

## Checklist

- [ ] Branched off `main`; changes are surgical (no unrelated refactors).
- [ ] `make verify` (or `make check`) passes locally.
- [ ] The `qa-gate` workflow is green.
- [ ] No spec was weakened to turn a red gate green (fidelity lint passes).
- [ ] For a new/changed pack: `r-coverage` was run and every GAP (a criterion not exercised, or a `covers`/`contract_claim` resolving to nothing) is resolved or explicitly accepted.
- [ ] Commit messages use a conventional prefix and carry no AI-attribution trailers.
- [ ] Rollback is a simple revert (changes are additive where possible).
