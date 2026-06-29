# Release Safety

> Reversibility discipline for a QA framework: test specs, test code, fixtures,
> page objects, shared test data, and diagnostics tooling. Lightweight by design —
> document how to undo a change, skip the formal release checklists.

---

## Core Principle

Every change must be reversible in minutes, without data heroics. Before you
commit, you must be able to answer: **"How do we undo this?"** Document the
answer; you do not need a formal checklist.

## Requirements

- **Identify the rollback path** and record it in the commit message or PR
  description whenever a change affects behavior (test outcomes, shared
  fixtures, framework core, or CI gating). Typical paths, fastest first:
  - **Revert the commit** — the default for most test/spec/fixture changes.
  - **Flip a flag or marker** — e.g. re-skip / re-`xfail` / quarantine a test,
    or toggle a config switch, without reverting code.
  - **Flip an alias or pointer** — e.g. repoint to a previous environment,
    dataset, or config version.
- **Prefer additive changes** — add the new thing before removing the old one.
  When replacing a test, fixture, or page object, land the replacement and
  verify it before deleting what it supersedes (avoid a coverage gap mid-change).
- **A plain `git revert` should be sufficient** for the majority of changes in
  this framework. If a change cannot be undone by a revert alone, say so
  explicitly and document the extra steps.

## Heightened-Rigor Triggers

Apply extra care — stage the change, verify the rollback path before merging,
and call it out in review — when a change touches any of the following:

- **Durable / long-lived shared test data** that other tests depend on
  (find-or-create baseline objects, seeded fixtures). Mutating or renaming these
  can break unrelated tests; deletion may be irreversible. Prefer additive,
  guard against accidental deletion of protected/long-lived objects.
- **Shared framework core or widely-used fixtures** — a change here fans out to
  many tests. Confirm the blast radius and that a revert cleanly restores prior
  behavior.
- **State in a shared test environment** — anything that creates, mutates, or
  deletes data other runs rely on. Ensure the change is self-cleaning or
  reversible; never leave a shared environment in a state a revert cannot fix.
- **CI gate or pipeline configuration** — a change that could block or mis-gate
  every merge. Have a one-step way to restore the prior gate (revert or flag).

When a trigger applies, the rollback path is not optional documentation — verify
it works before the change lands.
