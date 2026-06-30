# Personas & data durability

Every case declares a **persona** (`engine/case.py`); it determines how the case treats the data it
touches on a shared backend.

| Persona | Meaning | Data lifecycle |
|---------|---------|----------------|
| `new_user` | fresh-instance creation | creates ephemeral objects, **self-cleans** (`teardown`) |
| `existing_data` | durability / migration regression | operates on long-lived objects via **find-or-create**; **never deletes** them |

The `new_user` persona proves a feature works from scratch. The `existing_data` persona is the one
that catches **data loss on migration**: a durable object that silently fails to persist (or loses a
field) across a deploy. A suite that only ever creates throwaway objects cannot catch that.

## The naming + guard primitives (`engine/personas.py`)

```python
keep_name("account", "baseline")      # -> "qaf-keep:account:durability-baseline"   (durable, stable id)
ephemeral_name("conn")                # -> "qaf-ephemeral:conn:9f3a1c0b"             (unique, sweepable)
is_protected_name("qaf-keep:...")     # -> True  (the no-delete guard cleanup MUST honour)
find_or_create(find, create, name)    # -> (obj, created)  created=True only on the first run
```

- `keep_name` builds a **stable, prefixed** id so a durable object is found the same way on every run
  (idempotency) and is recognisably protected.
- `ephemeral_name` adds a uuid so a **missed** teardown leaves a harmless, uniquely-named, *sweepable*
  leftover (reaped out-of-band via the plugin's `sweep` hook).
- `is_protected_name` is the guard any cleanup/teardown/sweep path must consult — a `qaf-keep:` object
  is never deleted.
- The prefixes are plugin-configurable; the helpers are generic framework logic.

## Choosing the path

```mermaid
flowchart TD
  c([case declares persona]) --> p{persona?}
  p -- new_user --> e1[create ephemeral objects<br/>named with ephemeral_name]
  e1 --> e2["assert the behavioral contract"]
  e2 --> e3["teardown(sut): delete what was created<br/>(best-effort, in finally)"]
  e3 --> e4{teardown missed?}
  e4 -- yes --> e5[orphan left with a unique name<br/>→ reaped by sweep_ephemerals]
  e4 -- no --> done([clean])
  e5 --> done

  p -- existing_data --> d1["name = keep_name(...)"]
  d1 --> d2["obj, created = find_or_create(find, create, name)"]
  d2 --> d3{created?}
  d3 -- "yes (first run)" --> d4[create from in-code baseline<br/>assert the baseline]
  d3 -- "no (later run)" --> d5[read-and-verify the baseline persisted<br/>refuse to overwrite]
  d4 --> g["teardown: is_protected_name → NEVER delete"]
  d5 --> g
  g --> done
```

## Find-or-create across runs (the durability contract)

The worked example is `sut/mock-shop/packs/SHOP-DUR-account-durability/`, run against the mock's
**file-backed** account store (`sut/mock-shop/source/app.py`: `POST /accounts` is idempotent —
`201 created:true` the first time, `200 created:false` thereafter), so the durable genuinely survives
across server boots. `sut/restful-booker/packs/BOOK-DUR-room-catalog/` is the same pattern on a second
site (a durable file-backed *room*), proving the persona machinery is product-neutral.

```mermaid
sequenceDiagram
  participant Case as SHOP-DUR case
  participant FOC as personas.find_or_create
  participant SUT as SUTConnector
  participant Store as mock /accounts (file-backed)

  Note over Case,Store: Run 1 — the durable does not exist yet
  Case->>FOC: find_or_create(find, create, "qaf-keep:account:durability-baseline")
  FOC->>SUT: find → GET /accounts/{name}
  SUT->>Store: lookup
  Store-->>SUT: 404
  FOC->>SUT: create → POST /accounts {plan: enterprise}
  SUT->>Store: persist baseline
  Store-->>SUT: 201 {created: true}
  FOC-->>Case: (acct, created=True)
  Case->>Case: assert baseline (name, plan=enterprise)

  Note over Case,Store: Run 2 — the durable persisted
  Case->>FOC: find_or_create(...)
  FOC->>SUT: GET /accounts/{name}
  Store-->>SUT: 200 {plan: enterprise}
  FOC-->>Case: (acct, created=False)
  Case->>Case: assert baseline still holds
  Case->>SUT: POST /accounts {plan: downgraded}
  Store-->>SUT: 200 {created:false, plan: enterprise}
  Case->>Case: assert durable NOT overwritten
  Case->>Case: teardown → is_protected_name → no delete
```

## Why teardown lives in a `finally`

`engine/runner.py` calls `case.teardown(sut)` in a `finally`, so a `new_user` case self-cleans **even
if its body raised**. Cleanup is best-effort: a teardown error is logged (`~ teardown error
(ignored)`) and swallowed so it can never red the gate or abort the remaining cases. The default
`RegressionCase.teardown` is a no-op; a case overrides it to delete what it created — and a durable
case's teardown consults `is_protected_name` and refuses.

See also: [the regression gate](regression-gate.md), [targeting a real backend](remote-backend.md).
