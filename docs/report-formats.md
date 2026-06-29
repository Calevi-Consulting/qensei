# Report formats

The structures the [`/test-ticket`](../commands/test-ticket.md) and
[`/report-bug`](../commands/report-bug.md) commands produce. Product- and tenant-neutral; rich-text
fields render as ADF on the Jira provider (plain markdown on the mock provider).

## Test-execution result (test-ticket)

Written to the ticket (per the profile's `write_results` target) and to the run report:

```
Validation: <TICKET-ID> — <title>
Environment: <SUT> @ <env>   versions: <component versions>
Depth: <minimal|standard|deep>

Checks (<n> total):
  AC1 <criterion>            PASS
  AC2 <criterion>            FAIL — <what went wrong, observed vs expected, evidence ref>
  AC3 <criterion>            BLOCKED — <what blocks it>
  AC4 <criterion>            SKIPPED — <why>

Result: <PASS | FAIL | PARTIAL>
Evidence: runs/<TICKET-ID>_<ts>.md  (screenshots: runs/.../*)
```

Status vocabulary: **PASS / FAIL / SKIPPED / BLOCKED** per check; the roll-up transitions the ticket
only when every check passed (see test-ticket Phase 5).

## Bug report (report-bug) — six sections

Each section answers a different question for a different reader; do not repeat across them.

1. **Summary** (`summary`) — `[Impact/consequence] due to [technical issue]`. Lead with the "so
   what"; strictly factual; no vague words ("broken", "not working").
2. **Description** (`description`, ADF) — opens with Gherkin:
   ```
   Given <precondition>
   When <action>
   Then <observable result>
   ```
   then **Impact** (one sentence), **reproduction across environments**, inline screenshot
   description, related tickets (with plain-text previews). If an API error is involved, an
   `{expand:Affected Endpoint Details}` block with method/URL/code/body (first ~15 lines).
3. **Steps to Reproduce** (`steps_to_reproduce`, ADF ordered list) — step 0 = preconditions
   (data/state), step 1 = login with full URL, every navigation step with its full URL/request.
4. **Actual Behavior** (`actual_behavior`) — what is observed following the steps. Objective.
5. **Expected Behavior** (`expected_behavior`) — what should happen; if another environment is
   correct, cite it.
6. **Environment** (`environment`) — the SUT version block (URL + component versions).

**Improvement** variant — three sections: **Current behavior** (= steps + actual), **Proposed
improvement** (= expected), **Value** (why it matters). Issue type `Task`.

## Classification fields

Human-judged: component, priority, severity (bug), is-regression (bug), product-line. Auto-derived
via the profile's `bug` map: issue type, QA driver (current user), and any tenant default (e.g. a
defect type). `affects_version` is confirmed with the human before being set.

> Field ids are NOT in this document — they live per tenant in
> [`ticket/providers/jira.fields.json`](../ticket/providers/jira.fields.json). This format names only
> normalized fields, so it is the same on every Jira instance.
