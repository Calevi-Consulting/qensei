# SHOP-DUR — durable account persists with its baseline across runs

| Field | Value |
|-------|-------|
| Ticket | `SHOP-DUR` (no tracker — demo) |
| Area | accounts / durability |
| Automation layer | REST |
| Persona coverage | `existing_data` (durable find-or-create; never deleted) |
| Status | automated |
| Tags | `durability` |

## Context

Regression suites that only ever create throwaway objects cannot catch **data-loss on
migration**: a durable object that silently fails to persist (or loses a field) across a
deploy. This case operates on a long-lived account and asserts it keeps its baseline.

## Requirements

- A durable account `qaf-keep:account:durability-baseline` exists with `plan = "enterprise"`.
- If absent, it is created from that in-code baseline (first run).
- On every later run it is read-and-verified, never recreated, and never overwritten.

## Acceptance criteria

- [x] First run: the account is created with the baseline (`created == True`, HTTP 201).
- [x] Later runs: the account is re-used (`created == False`) and still holds the baseline.
- [x] A later write with a different plan does NOT overwrite the durable baseline.
- [x] The durable name is protected (`is_protected_name`), so teardown never deletes it.

## Risks & Assumptions

- The mock persists accounts to a gitignored file (`source/.accounts.json`); deleting it
  resets the "first run" path. A real backend persists in its own store. Rollback: none
  (read-mostly; the only write is the idempotent baseline create).

## Implementation

- Pack: `packs/SHOP-DUR-account-durability/`. Uses `engine.personas.find_or_create` +
  `keep_name` + `is_protected_name`.
