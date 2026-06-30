# Ticket provider contract — "ticket access"

A ticket provider is a small adapter that gives the framework a uniform **ticket** — the
input to `/spec-test`. It is the second plugin seam in the framework (the first is the
[SUT contract](../sut/contract.md), "backend access"): the engine, the spec-test entry
flow, and the lenses depend only on the *normalized* ticket, never on a specific issue
tracker. `mock-file` is the reference implementation used by the demo; `jira` is the
reference real provider, reached through the project's read-only Jira MCP/API.

The framework is tracker-agnostic the same way it is product-agnostic: swap the provider and
nothing in `engine/`, `core/`, or `policies/` changes.

## The normalized ticket

Every provider returns the same shape. This is the only ticket vocabulary the rest of the
framework knows.

| field | type | meaning |
|-------|------|---------|
| `id` | string | the tracker key / issue id (e.g. `SHOP-456`). Seeds the spec filename. |
| `title` | string | one-line summary. |
| `description` | string (markdown) | the narrative: what the feature/bug is and why. |
| `acceptance_criteria` | `[{text, checked}]` | the testable criteria. `checked` reflects whether the criterion was ticked during manual validation; `null` when the source has no checkbox semantics. |
| `status` | string | a **normalized** workflow status (`open` · `in_progress` · `in_review` · `done`), mapped from the tracker's own status name. |
| `links` | `[{type, url, title?}]` | related issues, the spec, design docs, MRs/PRs, domain learnings. |

```jsonc
{
  "id": "SHOP-456",
  "title": "Apply a 10% bulk discount at 3+ items",
  "description": "Checkout should reward larger baskets …",
  "acceptance_criteria": [
    {"text": "A cart below 3 items is charged full price.", "checked": true},
    {"text": "A cart of 3+ items receives 10% off the subtotal.", "checked": true}
  ],
  "status": "done",
  "links": [
    {"type": "spec", "url": "sut/mock-shop/specs/SHOP-456-bulk-discount.md", "title": "Spec"}
  ]
}
```

## Providers

Selected per run: `/spec-test --ticket <provider>:<id>` (e.g. `mock-file:SHOP-456`,
`jira:QA-1234`). The provider only ever **reads** — see *Read-only by default* below.

- **`mock-file`** (reference / demo) — reads a local markdown ticket from a site's own
  `sut/<name>/tickets/<id>.md`. Zero dependencies, no network, fully offline. This is what makes
  the spec-test entry flow runnable per site:
  [`sut/mock-shop/tickets/SHOP-456.md`](../sut/mock-shop/tickets/SHOP-456.md) normalizes to the
  shape above and maps to
  [`sut/mock-shop/specs/SHOP-456-bulk-discount.md`](../sut/mock-shop/specs/SHOP-456-bulk-discount.md);
  the booker site has [`sut/restful-booker/tickets/BOOK-2.md`](../sut/restful-booker/tickets/BOOK-2.md).
- **`jira`** (reference real) — fetches an issue through the project's **read-only Jira
  MCP/API**. No tracker credentials live in this repo; the provider uses whatever read-only
  Jira access the host project already configures. **The Jira field layout is configurable**
  (next section) so the provider works against *any* tenant, not one specific instance.

## The Jira field schema is configurable

Jira instances do not agree on where the data lives. Acceptance criteria might be a custom
field on one tenant, a heading inside the description on another; custom-field ids
(`customfield_10042` vs `customfield_11990`) are assigned per instance; workflow status names
are project-defined. So the `jira` provider does **not** hardcode any field — it reads a
per-tenant mapping from `ticket/providers/jira.fields.json` that maps each *normalized* field
to that tenant's actual Jira field id / path / extraction strategy.

```jsonc
// ticket/providers/jira.fields.json  — example for tenant A
{
  "provider": "jira",
  "base_url": "${JIRA_BASE_URL}",
  "auth": {
    "mode": "mcp",
    "note": "read-only via the project's Jira MCP/API; or {\"mode\":\"token\",\"token_env\":\"JIRA_TOKEN\"} for a read-only REST token"
  },
  "fields": {
    "id":          "key",
    "title":       "fields.summary",
    "description": "fields.description",
    "status":      "fields.status.name",
    "links":       "fields.issuelinks"
  },
  "acceptance_criteria": {
    "strategy": "custom-field",      // this tenant stores AC in a custom field
    "field":    "customfield_10042",
    "format":   "checklist"           // parse `- [ ] / - [x]` items
  },
  "status_map": {
    "Backlog": "open", "Selected for Development": "open",
    "In Progress": "in_progress",
    "In Review": "in_review", "Ready for QA": "in_review",
    "Done": "done", "Closed": "done"
  }
}
```

The same provider, pointed at a different tenant whose AC lives inline in the description
under a heading and whose statuses differ, needs only a different config — **no code change**:

```jsonc
// tenant B — AC parsed from a description section, different field ids
{
  "fields": { "id": "key", "title": "fields.summary",
              "description": "fields.description", "status": "fields.status.name",
              "links": "fields.issuelinks" },
  "acceptance_criteria": {
    "strategy": "description-section",  // no custom field; pull a heading out of the body
    "heading":  "Acceptance Criteria",
    "format":   "checklist"
  },
  "status_map": { "To Do": "open", "Doing": "in_progress", "QA": "in_review", "Shipped": "done" }
}
```

Mapping reference:

- **`fields.<normalized>`** — a dotted path into the Jira issue JSON (`fields.summary`,
  `fields.status.name`). Change the path, not the engine.
- **`acceptance_criteria.strategy`** — `custom-field` (read `field`), `description-section`
  (extract the `heading` section from the description), or `whole-description` (the entire
  body is the AC). `format` chooses the item parser: `checklist` (`- [ ]`/`- [x]`, preserves
  `checked`), `bullets`, `numbered`, or `lines`.
- **`status_map`** — maps the tenant's raw workflow status names onto the normalized set.
  Unmapped values pass through verbatim with a warning so a missing mapping is visible, not
  silently dropped.
- **`links`** — `fields.issuelinks` plus remote links are flattened to `{type, url, title?}`.

There is intentionally nothing tracker- or company-specific baked into the provider. A new
Jira tenant is onboarded by writing one `*.fields.json`, never by editing Python.

## The mock-file format

The `mock-file` provider parses a local markdown ticket so the demo runs offline. It reads:

- the H1 `# <KEY> — <summary>` → `id` (also taken from the filename) + `title`;
- a leading **metadata table** (`| Field | Value |`) → `status` (via the built-in
  `status_map`, overridable), plus any extra fields a tester recognizes (Type, Priority, …);
- the `## Description` section → `description`;
- the `## Acceptance Criteria` checklist (`- [ ]` / `- [x]`) → `acceptance_criteria[]`
  with `checked` preserved;
- the `## Links` markdown links → `links[]`.

This deliberately mirrors the `jira` provider's `description-section` + `checklist` strategy,
so the demo exercises the same normalization path a real tenant would. See
[`sut/mock-shop/tickets/SHOP-456.md`](../sut/mock-shop/tickets/SHOP-456.md) for the concrete file.

## The entry flow (ticket → spec)

The ticket is the **input** to `/spec-test`, not an output:

1. **Fetch + normalize** — the selected provider returns a normalized ticket.
2. **Manual validation is the source of truth** — a tester (or the AI manual-QA pass) has
   already validated the ticket against the running SUT; that evidence backs the spec.
3. **Human-approved spec** — the normalized `acceptance_criteria` seed a draft
   `sut/<name>/specs/<id>-<short-desc>.md`. The human owns intent and approves the spec; the
   criteria are never silently rewritten (see `policies/methodology.md`, *Ownership*).
4. **Automate** — `/spec-test` writes the pack/case and runs the regression gate.

So `mock-file:SHOP-456` → [`sut/mock-shop/specs/SHOP-456-bulk-discount.md`](../sut/mock-shop/specs/SHOP-456-bulk-discount.md)
→ `sut/mock-shop/packs/SHOP-456-discount/` is the full, runnable entry flow in the mock-shop domain.

## Read-only by default

A provider's job is to **read** a ticket. It does not transition issues, comment, or file
bugs. When a lens (e.g. **R-DIAGNOSIS**) concludes a failure is a `REAL_BUG`, it produces a
bug report and hands it to the **human** to open through the ticket provider — filing is an
outward-facing, human-gated action, kept off by default. Configure providers with read-only
safe defaults; do not embed tracker-specific allow/deny tool lists in this repo.

## Adding a new provider

1. Implement the provider so `fetch(id)` returns the normalized ticket shape above.
2. If the source has a configurable schema (any real tracker does), read it from
   `ticket/providers/<provider>.fields.json` — map normalized fields to the source's own
   fields/paths/strategies; do not hardcode them.
3. Keep it read-only; route any outward write through the human-gated path.
4. Wire it into selection: `/spec-test --ticket <provider>:<id>`.
