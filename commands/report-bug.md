# /report-bug — file a structured defect (or improvement)

Creates a **Bug** (something broken) or **Improvement** (works but could be better) in the ticket
system. The AI guides a human through a structured investigation, then writes a reproducible report.
Tenant-neutral: all field ids/values resolve through
[`jira.fields.json`](../ticket/providers/jira.fields.json); the report structure is in
[`docs/report-formats.md`](../docs/report-formats.md).

## Invocation

```
/report-bug [description] [--type bug|improvement] [--sut <name>] [--parent <TICKET-ID>] [--affects-version <v>] [--profile <jira-profile>]
```

`--type` defaults to `bug`; if unspecified, infer from the description (error/crash/regression →
bug; friction/missing-feedback/"would be better" → improvement) and ask if ambiguous.

## Principles

- **Never infer missing data — ask the human.** The AI investigates, structures, and writes; it does
  not guess.
- **Write for a reader without your environment.** Fewer words; no repetition across sections; every
  ticket reference carries a plain-text preview (`KEY - summary`); describe screenshots inline.

## Phase 1 — Understand the problem

Get the fundamentals before proceeding. **Bug:** what is wrong / why it's a problem / when it
happens / how often. **Improvement:** what should improve / during what action / why it's valuable.
If found during a `/test-ticket` run, pull context from the session but still confirm with the human.

## Phase 2 — Investigate

1. **Reproduce** against the SUT (REST via the SUTConnector, or the SUT's UI tools): exact step path,
   full URLs/requests, screenshots.
2. **Capture the failing call** if applicable: method, URL, payload, response code, body (truncate
   bodies > ~15 lines to an attached artifact).
3. **Reproduce across environments** (ask the human for others) — note whether it's env-specific.
4. **Duplicate check** — fast and bounded (< 2 min, ≤ 2 queries, ≤ 3 deep fetches): search by *where*
   the bug occurs (page/component), scan summaries, classify exact-duplicate (stop) / related
   (reference) / none (proceed).

## Phase 3 — Compose the report

Use the format in [`docs/report-formats.md`](../docs/report-formats.md). A **Bug** has six sections
(Summary, Description with a Given/When/Then + Impact, Steps to Reproduce, Actual Behavior, Expected
Behavior, Environment); an **Improvement** has three (Current behavior, Proposed improvement, Value).
The title leads with the consequence — `[Impact] due to [Technical issue]` — strictly factual.

## Phase 4 — Classification fields

Ask the human for the judgment fields (component, priority, severity[bug], is-regression[bug],
product-line). Auto-populate the derivable ones from the profile's `bug` map (issue type; QA driver
= current user; any tenant default such as a defect type). Confirm `affects_version` with the human
before setting it (infer from the SUT version block if available).

## Phase 5 — Preview and approval

Show the human the full preview — every applicable section and field as it will appear — and wait for
explicit approval (or proceed under `HARNESS_MODE=1`).

## Phase 6 — Create

Resolve each normalized field to its tenant field via the profile, render `adf` fields as ADF, create
the issue, then: output `<Type> created: <KEY> — <summary>`; remind the human to attach
screenshots manually; link to `--parent` if given.

## Test-execution integration

Invoked from a `/test-ticket` run: pre-fill Steps from the failing check, Environment from the
session, parent = the ticket under validation, and reference the failing check id in the description.

## Error handling

Jira rejects the create → show the error, ask for the missing field. User/account lookup fails → ask
for the account id. Invalid component → fetch and present options. Duplicate found → stop and confirm.
