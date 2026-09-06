# R-DESIGN — design-stage review lens

**Type:** LLM, advisory, read-only. **Authority:** none — findings land in an existing human gate.
**Agent:** `agents/r-design.md` · **Record lint:** `engine/design_panel_lint.py` ·
**Spec:** `specs/005-design-panel-and-invocation-tiers.md` WS-A.

The first lens that runs **before** code exists. Every other lens fires in `/automate` Phase 4, after a
design defect has already been implemented and has already cost a regression-gate cycle
(diagnose → fix → re-run, capped at 3 cycles per root cause).

## When it enters

- **Phase 2b**, once `sut/<name>/plans/<date>-<slug>.md` is drafted and **before** implementation —
  Tier 1, on every new pack, **as a subagent** (inline self-review by the plan's author is not a
  substitute; it is the same bias Phase 4's Tier 1 exists to check).
- Its findings surface at the **Phase-2 human approval gate that already exists**. It adds no gate, has
  no merge authority, and is not a slash command (a context-free trigger would run it with nothing
  concrete to review — the same reason the review panel is not one).
- `engine/coverage_lint.py` runs **first** where a pack exists. A deterministic answer is never spent on
  a lens.

Tier 2 escalation, on its flags: `needs_mechanism` → **R-MECHANISM** verifies the mechanism claim against
the SUT source (or the ticket/doc snapshot for a sourceless SUT), and its citations go through
`engine/citation_gate.py`. `needs_evidence` → **R-EVIDENCE**.

**Who decides.** The **human**, at the spec-approval gate. The GENERATOR writes a *proposed* disposition
per finding into the plan (`- F<n> APPLIED|REJECTED|FLAGGED|DEFERRED: <reason>`, gated for presence and
count by `engine/design_panel_lint.py`); the human ratifies or overrides it. There is deliberately **no
JUDGE at Phase 2b**: the phase already stops at a human one step later and fields one or two lenses with
at most six findings — no dedup, no rebuttal protocol, nothing for a judge to do that the approval gate
does not. Adding one would put an adjudicator in front of an adjudicator and make an advisory lens the
de-facto design gate. Revisit only if 2b grows to three or more lenses with overlapping findings.

## How its check works

Ten checklist items, applied to the (spec, plan) pair with the ticket, the SUT source (via the
SUTConnector), both knowledge stores, the sibling pack index cards and the manifest in context:

| # | Item | The defect it catches |
|---|---|---|
| 1 | Ticket scope → AC traceability (walk the ticket) | a criterion the ticket asked for that was never written — invisible to every downstream gate |
| 2 | Criteria vs the risk the ticket carries | ACs that restate the happy path; a threshold pinned on one side only |
| 3 | Persona | a durability claim tested on an object created in-test |
| 4 | REST-first vs UI | a `UICase` where an API path exists |
| 5 | Precondition ↔ assertion decoupling | the false-SKIP class: the case skips exactly when the bug appears |
| 6 | Cross-pack reuse | rebuilding a durable a sibling pack already find-or-creates; a silent second owner |
| 7 | Shared state under `-n auto` | two cases mutating one durable / one un-reset global on the same runtime |
| 8 | Write-then-read synchrony | a read taken before an async write settles → `needs_mechanism` |
| 9 | `covers` / `contract_claim` vs what the plan exercises | metadata that resolves but is wrong — corrupts DESIGN's report and DIAGNOSE's verdict |
| 10 | Sourceless SUT | a mapping presented as source-confirmed when there is no source |

Output is capped at **six** findings, each with its checklist item, a severity, a `file:line` or an
explicit `hypothesis:` label, and one concrete alternative. "Nothing is wrong" is a valid, one-line
answer — a lens that always finds something becomes noise, and noise gets waived.

## What errors it must catch

Each of these is a real, dated case — from this repo where one exists, from the framework the panel was
ported from otherwise — which is why it is on the list:

| Case | Item |
|---|---|
| **`BOOK-UI-2` (PR #26, spec 004 § Context)** — the UI case was hand-copied from `BOOK-UI-1`; its `run()` initially ran the happy-path booking and its `covers` listed `POST /booking/`, an endpoint the validation-error scenario never exercises. `coverage_lint` would have passed it: the route *resolves*. Only a reader asking "does `covers` name what this plan exercises?" catches it | 9 |
| **`SHOP-456`** as the positive example — the spec pins **both** sides of the ≥3 threshold because `SHOP_LEARNINGS` records the off-by-one class; a plan asserting only "a discount applies" would pass green and miss the regression the rule is famous for | 2 |
| Source framework, 2026-08-27 — a ticket's scope item named a host-side check explicitly; the spec collapsed it with a platform-side signal into one AC written against the layer that already had a helper. It survived the lens (whose prompt never asked about ticket coverage), reached implementation and two live cycles, and was caught by a human reading the spec | 1 |
| Source framework — two packs contributed **0 executed tests** on both arms of a green full run: their pre-flight asserted the condition the tests asserted, so every case skipped exactly when it would have failed | 5 |
| Source framework — a cancel-then-export arm passed locally and failed the gate twice on identical data: the cancel emitted events a consumer applied later, and the export — always read first — was captured mid-propagation | 8 |
| Source framework — a pack consuming a producer pack's existing durable run removed a ~22-minute end-to-end fixture | 6 |

## "Read-only" is a prompt constraint plus a tool allowlist

The frontmatter grants `tools: Read, Grep, Glob, Bash` and puts `Write, Edit, MultiEdit, NotebookEdit` in
`disallowedTools`, like every lens in `agents/`. Two caveats (`agents/README.md` § Notes): the limits apply
when the agent is loaded at session start, so a lens wired mid-session transiently has the full toolset
until Claude Code restarts; and `Bash` stays granted for read-only shell (`git`, `engine.freshness_gate`),
so a shell-driven write is bounded by the prompt discipline, not tool-blocked. Read a lens's findings;
do not assume the sandbox enforced the contract.

## The honest limit

R-DESIGN catches **bias** errors — a design its author is too close to question. It does **not** close
**knowledge gaps**: it cannot know a SUT behaviour nobody has written down, and a confident wrong finding
at design time is worse than none, because it gets built into the pack rather than caught by a failing
case.

That asymmetry sets its lifecycle: **every finding that recurs must graduate into a lint.** The
precedent is R-COVERAGE, whose mechanical half became `engine/coverage_lint.py` while the semantic half
(does `run()` exercise the criterion?) stayed with the lens. Items 5, 7 and 9 are candidates — item 9
already has its deterministic companion in `coverage_lint` (resolution), which is why R-DESIGN's job there
is only the part a rule cannot decide: whether the metadata that resolves is the *right* metadata.

Item 8 exists **because** of that limit rather than in spite of it. A write-then-read race is not a
design opinion — it turns on a SUT fact (does a consumer apply this write later?) that the plan's author
does not have. So the item's job is not to answer the question but to *notice that the plan assumes an
answer*, and to route it to R-MECHANISM via `needs_mechanism`. That is the general shape for anything in
the knowledge-gap column: R-DESIGN cannot close it, but it can refuse to let it pass unnamed.

## Freshness is not optional here

R-DESIGN reviews a plan whose REST mapping cites the SUT source, so it inherits the same exposure as
R-MECHANISM and runs the same self-gate first (`python3 -m engine.freshness_gate --sut <sut>`). For an
`in_process` mock or a sourceless SUT the gate is a no-op; for a `remote` SUT with a stale clone the lens
**stops** and says so rather than reviewing behind a caveat. It also cannot see runtime: it reads intent
and mechanism; the gate is still the only source of truth for whether the pack is green.
