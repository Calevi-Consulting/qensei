## What

<!-- One or two sentences: what changed and why. -->

## Context

<!-- Link the ticket or issue, if one exists. -->

## Checklist

- [ ] Branched off `main`; changes are surgical (no unrelated refactors).
- [ ] `make verify` (or `make check`) passes locally.
- [ ] The `qa-gate` workflow is green.
- [ ] No spec was weakened to turn a red gate green (fidelity lint passes).
- [ ] Commit messages use a conventional prefix and carry no AI-attribution trailers.
- [ ] Rollback is a simple revert (changes are additive where possible).
