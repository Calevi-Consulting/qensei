# Checkpoints — named known-good states

A checkpoint is a git tag `cp-NNN` on a commit whose gate was green on every configured
environment — a known-good state to roll back to. Cut one on request at a milestone (not
automatically). Rollback is `git reset --hard cp-NNN` (local) or `git revert <range>` (shared).

| Tag | Date | Commit | Green state | Notes |
|-----|------|--------|-------------|-------|
| cp-000 | <date> | <sha> | `make demo` green; engine units pass | initial gap-closure baseline |
