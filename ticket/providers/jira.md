# Jira ticket provider

The reference implementation of the [ticket provider contract](../contract.md). It reads a ticket
from Jira and writes results, transitions, and bug reports back — through the host project's Jira
MCP/API. It is **tenant-neutral**: every field is resolved through
[`jira.fields.json`](jira.fields.json), never hardcoded, so the same provider works on any Jira
instance by selecting a profile.

## Configuration

- Select the active tenant profile in `jira.fields.json` (`active_profile`), or pass `--profile <name>`.
- A profile carries `cloud_id`, `project_key`, the `read` map (Jira field → normalized field), the
  `write_results` target, the `bug` field map, and the `transition` rules.
- Onboarding a new tenant = copy the `default` profile, fill the `REQUIRES_MAPPING` ids from your
  instance's field metadata (`getJiraIssueTypeMetaWithFields` or equivalent), and select it. No
  command or code changes.

## Normalized ticket

The provider returns every ticket in the shape the commands consume — independent of how the tenant
stores it:

```
{ id, title, description, status, acceptance_criteria[], labels[], components[], issue_type, links[], comments[] }
```

`acceptance_criteria` is extracted per the profile's `read.acceptance_criteria.strategy`
(`description-heading` parses a heading section; `custom-field` reads a dedicated field; other
strategies can be added) — because one tenant keeps ACs in a custom field and another as a heading
inside the description.

## Write logic (preserved from the source workflow, parameterized)

These rules are kept verbatim from the manual-QA discipline; only the field ids are now config-driven:

- **Approval gate — one per write.** Before any Jira write (result, field edit, transition, issue
  creation) show the human *what* will be written, *where*, and *why*; wait for approval. `HARNESS_MODE=1`
  skips the gate and logs that it did.
- **Resolve required fields first.** Read the issue-type field metadata; if a required field is
  unset and not derivable, stop and ask, showing the available options. Resolve before the write.
- **Rich text = ADF.** Fields typed `adf` in the map are rendered as Atlassian Document Format
  (ordered lists for steps, `{expand}` blocks for endpoint/log detail, `{code}` for payloads).
- **Plain-text preview for every Jira reference.** Render links as `KEY - summary`, never a bare key.
- **Content language** follows the profile's `content_language` (default `en`).
- **Secret masking** applies to all written content (`***MASKED***`).

## Transitions

Discover transitions dynamically (`discover_dynamically: true`) — never hardcode transition ids;
prefer local over global transitions. A pass-transition targets one of `transition.pass_target`, and
is gated on `transition.required_before_transition` (e.g. a product-line / fix-version field) being
set first, behind its own approval. A failing validation never transitions.

## Mock alternative

For local/demo runs with no Jira, the `mock-file` provider (see [contract.md](../contract.md)) reads
a markdown ticket from a site's own `sut/<name>/tickets/` and "writes" results to the run report
instead of a live instance — same normalized shape, so the commands are identical.
