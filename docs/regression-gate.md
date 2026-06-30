# The regression gate

The gate is the REGRESS capability: `engine/run.py` drives `engine/runner.py` to discover every
pack, run it against the live backend, and exit non-zero if anything fails — so CI can gate a merge
on it. Green is a precondition to landing.

```bash
python3 -m engine.run --sut sut/mock-shop                 # full gate
python3 -m engine.run --sut sut/mock-shop --select smoke  # one lane
python3 -m engine.run --sut sut/mock-shop --report report.xml   # + JUnit artifact
make test            # the full gate
make smoke           # the smoke lane
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | every selected case passed (or skipped under `partial` with at least one real pass) |
| `1` | at least one case FAILED |
| `2` | the **false-green guard** tripped — no cases ran / all skipped / SUT unreachable / credentials unresolved |

The exit-2 guard (`engine/run.py:_precheck`) exists so an empty or all-skipped run can never report
success — a run that verified nothing must not be mistaken for a green gate.

## Per-case lifecycle

Each case runs from a clean state, with pre-flight evaluated first and teardown guaranteed:

```mermaid
flowchart TD
  start([discover_cases under sut/&lt;name&gt;/packs/*/case.py]) --> filt{selection.matches<br/>tags vs --select?}
  filt -- no --> skip1[drop from this lane]
  filt -- yes --> pf{preflight.evaluate<br/>unmet requires?}
  pf -- "unmet & partial" --> SKIP[/status = SKIP<br/>reason recorded/]
  pf -- "unmet & block" --> FAILb[/status = FAIL<br/>blocked/]
  pf -- "all met" --> iso["sut.isolate()<br/>(plugin/manifest hook)"]
  iso --> runc["case.run(sut, expect)"]
  runc --> exc{raised?}
  exc -- "PreconditionError" --> precond[/error = PRECONDITION<br/>_precondition_failed = True/]
  exc -- "other exception" --> err[/"error = repr(e)"/]
  exc -- "no" --> softs{expect.failures?}
  precond --> td
  err --> td
  softs -- yes --> FAIL[/status = FAIL/]
  softs -- no --> PASS[/status = PASS/]
  FAIL --> td["teardown(sut) in finally<br/>(best-effort)"]
  PASS --> td
  td --> nextc([next case])
```

Key properties (`engine/runner.py`):

- **Selection before preflight** — a lane (`--select`) is filtered first, then requirements are
  evaluated only for the cases that remain.
- **`isolate()` is a hook, not a hardcoded endpoint** — the runner calls `sut.isolate()`, which uses
  the plugin's `isolate(sut)` or the manifest's `runtime.isolate` path (the mock's `/cart/clear`),
  else a no-op. The generic runner stays product-neutral.
- **Teardown always runs** — `case.teardown(sut)` is called in a `finally`, best-effort: a cleanup
  error is logged and swallowed so one failure cannot abort the rest of the gate.
- **A precondition is a real verdict** — `expect.precondition(...)` raises `PreconditionError`, which
  the runner tags so [diagnostics](diagnostics-and-review-panel.md) classifies it as a genuine failure,
  not transient infrastructure.

## Call sequence of a run

```mermaid
sequenceDiagram
  participant Main as run.main
  participant Set as Settings.load
  participant SUT as SUTConnector
  participant Runner as runner.run_packs
  participant PF as preflight
  participant Case as RegressionCase
  participant Rep as report

  Main->>Set: load(QAF_* + .env + CLI overrides)
  Main->>SUT: SUTConnector(sut_dir, settings)
  Note over SUT: resolves base_url + auth headers (may exit 2 if creds fail)
  Main->>SUT: start(buggy=…)
  Main->>SUT: reachable()?  %% remote only — exit 2 if not
  Main->>Runner: run_packs(sut, packs, select, preflight)
  Runner->>Runner: discover_cases() + selection.matches
  loop each selected case
    Runner->>PF: evaluate(case, sut, registry)
    alt unmet (partial)
      Runner-->>Runner: status SKIP
    else met
      Runner->>SUT: isolate()
      Runner->>Case: run(sut, expect)
      Runner->>Case: teardown(sut)  %% finally
      Runner-->>Runner: status PASS / FAIL
    end
  end
  Runner-->>Main: results [(case, expect, error, status)]
  opt --report
    Main->>Rep: write_report(results, path)
  end
  Main->>Main: _precheck(results)  %% false-green guard → exit 2
  Main-->>Main: exit 1 if any FAIL else 0
```

## The report artifact

`--report report.xml` writes JUnit XML (a CI "Tests" tab renders it); `--report report.json` writes
JSON for triage tooling (`engine/report.py`). Each case becomes a `<testcase>`; a SKIP is `<skipped>`,
a FAIL carries the collected failure details. In CI the gate uploads it as an artifact even on failure
(`.gitlab-ci.yml`, `artifacts.when: always`).

See also: [pre-flight & selection](preflight-and-selection.md), [personas & durability](personas-and-durability.md).
