# WIDGET-1 — A created widget starts active

## Status: COMPLETE

## Context

`widget-api` is a **sourceless** SUT: Qensei has no readable backend source, so this spec's
intent comes from the ticket ([`WIDGET-1.md`](../tickets/WIDGET-1.md)) and the skills doc
([`WIDGET.md`](../skills/WIDGET.md)), not from `ROUTES` / `BUSINESS_RULES`. A live runtime still
backs the gate.

## Requirements

Creating a widget returns the widget with status `active`, and a subsequent read shows the same.

## Acceptance Criteria

- [x] `POST /widgets {name}` returns `201` with the created widget.
- [x] A newly created widget has status `active`.
- [x] `GET /widgets/{id}` returns the same widget, still `active`.

## Risks & Assumptions

- **Sourceless:** the contract of record is the ticket; a failure diagnoses as `INDETERMINATE`
  (no independent source oracle). None beyond standard otherwise.

## Implementation

- Pack: [`packs/WIDGET-1-create-widget/`](../packs/WIDGET-1-create-widget/case.py).
