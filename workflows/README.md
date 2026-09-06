# `workflows/` — Workflow-tool orchestrators (canonical source)

Deterministic-control-flow orchestrators for the review panel, run via the **Workflow tool**. They
**reuse the `agents/*.md` lenses** (dispatched with `agentType`) and the `engine/` gates (run as
single-purpose mechanical steps) — the orchestration is here; the lenses and the gates are unchanged.

Canonical scripts live here and are versioned; `scripts/install.sh` symlinks
**`.claude/workflows -> ../workflows`** (gitignored), mirroring `commands/` and `agents/`.

## Why this exists alongside the model-driven protocol

`docs/multiagent/review-panel.md` is the **source of truth** for the panel sequence. There are two ways
to run it, and they coexist because the lenses are orchestrator-agnostic:

- **Model-driven** (the default) — the driving agent *follows* the protocol, dispatching the lenses as
  subagents. No JS, native to `/automate` Phase 4 inline, adapts to whatever the failure turns out to be.
- **Workflow** (this directory) — a script that *implements* the protocol deterministically. Use it when
  its advantages pay: `/workflows` live observability, dispatch that cannot be skipped or reordered,
  schema-validated findings, and scale (a future streaming/dedup layer would call it once per deduped
  root cause).

The Workflow tool spawns several agents, so it runs only when the human asks for it. That is the point of
the split: the always-on path stays the cheap one.

## review-panel.js

Runs the panel on ONE failing or changed case:

**ORIENT** (always, read-only, `general-purpose`) → **`engine.diagnostics`** (mechanical, when `pack` is
given) → **R-DIAGNOSIS** (always, freshness self-gated) → **R-EVIDENCE / R-MECHANISM** (conditional on
R-DIAGNOSIS's `needs_evidence` / `needs_mechanism`, in parallel) → **`engine.citation_gate`** (mechanical,
over the assembled findings) → **JUDGE** (decide + escalation digest).

Two things are deliberate. The conditional skip is a **branch on structured flags**, not a judgement, so a
non-mechanism failure never pays for R-MECHANISM. And the two `engine/` gates run as their own steps: the
JS sandbox has no shell, so a single-purpose step-agent runs the command and the script injects the
structured result downstream — the citation gate is a step the JUDGE *receives*, not an instruction it
must remember.

**Phase 0 · ORIENT** reads the RECORD before anyone reasons: the pack index card's gotchas, the spec's
acceptance criteria, any plan's `## Design panel` record (findings already REJECTED or DEFERRED at design
time), both knowledge stores, and prior validation reports' `### Panel` lines. It is **not a lens** — it
makes no judgement and returns no verdict; it returns what the repo already knows so the lenses argue
against it instead of rediscovering it. Two fields carry most of the value: `rejected_fixes` (re-proposing
one burns a cycle) and `contradicts_subject` (premises in the caller's brief that the record disputes — the
brief's author can be wrong). `prior_attempts` is the JUDGE's loop-budget input. Best-effort: if it returns
nothing the panel proceeds, and every downstream prompt says the record is absent.

### Input

`args` must be an **object**:

| Key | Required | What |
|---|---|---|
| `sut` | **yes** | the SUT plugin dir, e.g. `sut/mock-shop`. Every lens reads the system through that plugin's SUTConnector — freshness, citations and the diagnostics oracle are all per-SUT |
| `failure` · `env` · `pipeline` · `spec` · `diff` · `pack` | **at least one** | the subject. `pack` (a pack dir) additionally enables the deterministic `engine.diagnostics` step |
| `seed_bug` | no | `true` reproduces a regression with `engine.diagnose --seed-bug` (what `make diagnose-realbug` runs). Without it the mechanical step re-runs a *healthy* pack and reports `NO_FAILURE`, contradicting a brief that describes a regression |

Passing a **string**, or an object with `sut` missing, or one whose six subject fields are all empty,
**throws** rather than convening a panel against a null subject. That silent degradation is the failure
mode worth naming: every lens runs, the citation gate passes *vacuously* over an empty claim set (exit 0
reads like a clean bill of health), and the caller gets an authoritative-looking `ESCALATE` whose real
content is "no subject was supplied". A workflow error cannot be mistaken for an adjudication.

### Output

```js
{ decision, digest, record, diagnostics, diagnosis, lenses, citation_gate, verdict }
```

`decision` is one of `BLOCK | FIX | FLAG | ESCALATE | PANEL_CLEAR`. Two early returns short-circuit the
rest: R-DIAGNOSIS returning nothing, and a **stale SUT source** (its freshness self-gate) — both
`ESCALATE`, because a panel that never diagnosed, or one citing an old clone, has nothing to adjudicate.

### Invoking it

Via the Workflow tool, with `name: 'review-panel'` (through the symlinked `.claude/workflows`) or
`scriptPath: 'workflows/review-panel.js'`:

```js
Workflow({
  scriptPath: 'workflows/review-panel.js',
  args: {
    sut: 'sut/mock-shop',
    pack: 'sut/mock-shop/packs/SHOP-456-discount',
    seed_bug: true,
    failure: '<the gate/diagnose output for the failing case>',
  },
})
```

**The panel is advisory and never gates a merge.** The regression gate (`engine/run.py` / `make test`,
green on every configured environment) remains the source of truth for green; the human owns convergence.
No verdict here may weaken an acceptance criterion.
