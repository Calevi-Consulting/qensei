# WIDGET-1 — a created widget starts active

Sourceless-SUT demo pack. Creates a widget via `POST /widgets` and asserts it comes back
`active`, then re-reads it. Persona `new_user` (the stub runtime is ephemeral, so nothing
durable is left behind).

- **Spec:** [`WIDGET-1-create-widget.md`](../../specs/WIDGET-1-create-widget.md)
- **Covers:** `POST /widgets`, `GET /widgets/{id}`
- **Contract of record:** the ticket ([`WIDGET-1.md`](../../tickets/WIDGET-1.md)) — this SUT is
  **sourceless**, so there is no backend `BUSINESS_RULES` to diagnose against; a failure here is
  `INDETERMINATE` (the ticket is the authority).
- **Run:** the sourceless demo runs via `tools/tests/test_sourceless.py` (boots the stub and drives
  the real gate). Standalone: start `stub_runtime.py`, then
  `python3 -m engine.run --sut sut/widget-api --base_url http://127.0.0.1:<port>`.
