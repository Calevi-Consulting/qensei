# Widget service — manual-QA notes (sourceless SUT)

Qensei has **no source** for this backend; this file plus the ticket are the contract authority.
This is the "product documentation" a sourceless SUT leans on in place of readable source.

## Shape

- `POST /widgets {name}` → `201 {id, name, status}`. A new widget starts **active**.
- `GET /widgets/{id}` → `200` the widget, or `404`.
- `GET /widgets` → `200` the list.

## Gotchas

- The **active-on-create** default was a deliberate scope change (see the WIDGET-1 comments) —
  do not assume `pending`.
- The demo stub enforces no auth; a real deployment requires a token (`creds.mode`).
- No `DELETE` on the demo stub — the runtime is ephemeral, so `new_user` cases self-clean by
  virtue of the stub resetting on each boot.
