# `sut/` — the products under test (these are **replaceable examples**)

Every product Qensei tests is a **plugin** under `sut/<name>/` (the contract is in
[`sut/contract.md`](contract.md)). The plugins shipped here are **reference examples** — a real
adopter deletes them (or keeps one as a live reference) and adds plugins for their own products.
Nothing in `engine/` or `policies/` is product-specific.

| Plugin | What it demonstrates |
|---|---|
| `mock-shop` | the reference SUT — an in-process mock backend (products / cart / checkout), source + runtime |
| `restful-booker` | fuller example — adds `plugin.py` (live cookie-auth), a `ui-packs/` Playwright lane, and a `live` remote env |
| `restful-booker-live` | the same site pointed at a real remote host (no in-process mock) |
| `widget-api` | a **sourceless** SUT — no readable backend source; the ticket + `skills/` are the contract of record |

## Add your own product

```bash
make new-sut SUT=sut/<your-product>              # sourced (design reads its ROUTES + BUSINESS_RULES)
make new-sut SUT=sut/<your-product> SOURCELESS=1 # no readable source; the ticket is the contract
make new-pack SUT=sut/<your-product> TICKET=<T> SLUG=<slug>
```

The engine, the deterministic gates, and the CI / pytest **site matrices auto-discover** whatever
lives here (via `engine/sites.py` + glob) — you do **not** edit `engine/`, the CI matrix, or the
pytest bridges. See [`contract.md` § Adding a new SUT](contract.md#adding-a-new-sut-a-new-site).

## Removing the example SUTs

Deleting an example plugin dir is safe for the engine and gates (glob-discovered), but a few
**non-engine** spots reference the examples by name. See
[`contract.md` § Replacing the shipped example SUTs](contract.md#replacing-the-shipped-example-suts)
for the checklist (Makefile demo defaults, the example-coupled framework tests, and the docs that
narrate `mock-shop` / `SHOP-456`).
