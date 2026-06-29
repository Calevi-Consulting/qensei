# BOOK-DUR — durable room persists with its baseline across runs

| Field | Value |
|-------|-------|
| Ticket | `BOOK-DUR` (no tracker — demo) |
| Area | rooms / durability |
| Automation layer | REST |
| Persona coverage | `existing_data` (durable find-or-create; never deleted) |
| Status | automated |
| Tags | `durability` |

## Context

Regression suites that only ever create throwaway objects cannot catch **data loss on
migration**: a durable object that silently fails to persist (or loses a field) across a
deploy. This case operates on a long-lived room and asserts it keeps its baseline price.
It is the booker-site proof that the persona machinery is product-neutral — the same
`find_or_create` + `keep_name` + no-delete guard as mock-shop's SHOP-DUR.

## Requirements

- A durable room `qaf-keep:room:durability-baseline` exists with `roomPrice = 250`.
- If absent, it is created from that in-code baseline (first run).
- On every later run it is read-and-verified, never recreated, and never overwritten.

## Acceptance criteria

- [x] First run: the room is created with the baseline (`created == True`, HTTP 201).
- [x] Later runs: the room is re-used (`created == False`) and still holds the baseline.
- [x] A later create with a different price does NOT overwrite the durable baseline.
- [x] The durable name is protected (`is_protected_name`), so teardown never deletes it.

## Integration-boundary AC
- [x] The case exercises the real `/room/` endpoint of the SUT runtime; against the file-backed
  mock the room survives a server reboot, so a second run genuinely takes the re-read path.

## Risks & Assumptions

- The mock persists rooms to a gitignored file (`source/.rooms.json`); deleting it resets the
  "first run" path. A real backend persists in its own store. Rollback: none (read-mostly; the
  only write is the idempotent baseline create).

## Status: COMPLETE
Automated by `sut/restful-booker/packs/BOOK-DUR-room-catalog`. Uses `engine.personas.find_or_create`
+ `keep_name` + `is_protected_name`.
