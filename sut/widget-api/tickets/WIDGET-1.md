# WIDGET-1 — A created widget starts active

> Sourceless-SUT demo ticket. Qensei has **no source** for `widget-api`, so THIS ticket (+ the
> [skills doc](../skills/WIDGET.md)) is the contract authority. The `mock-file` provider
> normalizes it to `{id, title, description, acceptance_criteria[], status, links[], comments[]}`
> (see [`ticket/contract.md`](../../../ticket/contract.md)).

| Field | Value |
|-------|-------|
| Key | WIDGET-1 |
| Type | Story |
| Status | Done |
| Verified by | QA — manual pass against the widget service, **outside Qensei** |

## Description

Creating a widget via `POST /widgets {name}` should return the new widget with status `active`.
There is no backend source available to Qensei; this ticket is the source of truth for the contract.

## Acceptance Criteria

- [x] `POST /widgets {name}` returns `201` with the created widget.
- [x] A newly created widget has status `active`.
- [x] `GET /widgets/{id}` returns the same widget, still `active`.

## Comments

- **product-owner** (2026-07-01): heads up — the "active" default is a **late scope change**; earlier
  drafts defaulted to `pending`. The pack must pin `active`, that was the whole point of the change.
- **qa-lead** (2026-07-02): validated manually against staging — `POST` returns 201 with `status=active`.
  No Qensei `/validate` run yet; automating straight from this ticket.

## Links

- [type: spec] [WIDGET-1 spec](../specs/WIDGET-1-create-widget.md)
- [type: skills] [Widget service notes](../skills/WIDGET.md)
