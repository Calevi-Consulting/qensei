# Test Philosophy

AI tools can produce tests rapidly, but speed of test creation is not the same as quality of test design. Tests encode commitments about how the system under test behaves. The wrong tests create maintenance burden without meaningful safety.

> Influenced by Ábel Énekes, ["When Change Becomes Cheaper Than Commitment"](https://www.abelenekes.com/when-change-becomes-cheaper-than-commitment) (2026), applying the divergence/convergence model to AI-assisted development.

## Tests Are Contracts, Not Coverage

Every test is an implicit contract: "the system must continue to behave this way." The value of that contract depends on what it commits to and how long that commitment lasts.

| Contract Type | Example | Lifespan | Refactor Survival | Value |
|---------------|---------|----------|-------------------|-------|
| **User-facing behavioral** | "Login returns a session token" | Long — tied to product promises | High — survives internal rewrites | High |
| **Integration boundary** | "Service A calls Service B with the correct payload" | Medium — tied to API contracts | Medium — survives internal changes | Medium |
| **Implementation detail** | "Function X calls mock Y with args Z" | Short — tied to current code structure | Low — breaks on any refactor | Low unless isolating specific logic |

**Prioritize long-lived contracts.** Tests that verify what the system does for users survive architectural changes. Tests that verify how the internals are wired break when the implementation is refactored — even when behavior is unchanged.

## The "Mock the Universe" Anti-Pattern

If a test requires mocking many dependencies to achieve isolation, that is a signal — either the unit under test has too many dependencies (refactor it), or the test is at the wrong level of abstraction (move it higher and exercise the real system under test).

**Symptoms**:
- Test setup is longer than the test itself
- Mocks encode internal call sequences and argument shapes
- Changing one function's implementation breaks tests for unrelated features
- The test suite resists refactoring rather than enabling it

**Guidance**:
- Use mocks sparingly and deliberately, not as the default approach
- Prefer testing through public interfaces and real collaborators where practical
- When mocks are necessary, mock at architectural boundaries (external APIs, datastores, third-party services), not between internal modules — and never mock the system under test itself
- If you find yourself mocking more than 2–3 dependencies for a single test, reconsider the test's abstraction level

## Coverage Measures Exercise, Not Intent

Coverage tells you which code paths were executed during tests. It does not tell you whether those tests encode meaningful commitments. A 95% coverage number built on heavily-mocked unit tests may provide less real safety than 60% coverage built on integration tests that verify actual behavior.

**Guidance**:
- Do not treat coverage as a target to maximize. Treat it as a diagnostic — low coverage on critical paths is a signal; high coverage via brittle mocks is not safety
- When adding a test, ask: "What behavioral contract does this encode? Will the contract still matter after the internals are refactored?"
- Surface test-strategy decisions for human review: test level (unit vs. integration vs. e2e), mock boundaries, and what behavioral contracts the tests will encode

## AI-Generated Tests Require Human Judgment

AI tools write tests that match the code they just wrote. By construction, those tests pass. But passing is not the same as encoding a meaningful commitment. AI-generated tests tend toward implementation-coupled unit tests because the model has full visibility into the internal structure and reaches for it.

**Guidance**:
- Treat an AI-generated test suite as a starting point for human review, not a finished artifact
- During review, evaluate tests for contract quality: do they test behavior or implementation?
- When proposing tests, state what behavioral contract each test encodes
- Flag tests that would break on refactoring without any behavior change — these are implementation contracts with short lifespans

## Integration / E2E Tests Are Load-Bearing for AI-Assisted Work

Unit tests are necessary but not sufficient. AI-generated code is unusually prone to a specific failure mode: every isolated piece is correct, but the gap *between* the pieces — the part no unit test exercises — is wrong. Mocks make this strictly worse: the model invents the mock, invents the contract, and writes a test that passes against its own invention.

**The rule**: When a scenario crosses an integration boundary (database schema or ORM write path, message-queue offset/commit semantics, external API call, search-index sync, async/background job, multi-service write path, signal/event handler chain), at least one acceptance criterion must specify a runtime verification step that exercises a **real downstream system — not a mock**. Unit-test-only acceptance criteria on integration-boundary work are insufficient.

**What counts**:
- A query-count assertion that runs against a real test database
- A nightly / staging e2e check that asserts the field is populated after a real write or sync
- A test that produces to a real message queue and asserts on real consumer behavior
- A test that hits a real downstream API in a sandbox environment

**What does not count**:
- A unit test with the integration boundary mocked
- A "behavioral" test where the assertion is on the in-memory object *before* the write
- Coverage of the function that builds the payload, without coverage of the write itself

### Case Study: Silent Field Drop in a Batch Update

A representative AI-typical failure caught only by real-system verification. A new field was added to a record type and assigned in memory, but the persistence call was a **batch update that writes only an explicit list of fields** — and the new field was never added to that list. The fix was one line: add the field to the update's field list.

**Layers that passed**:
- The helper that computed the new field's value returned correct results — unit tests covered bounding, rounding, and null handling
- The in-memory assignment happened — the object in memory was always correct
- A behavioral test confirmed the write path was invoked
- Code review passed — the assignment and the batch-update call both look correct in isolation
- Logs showed `updated=N` with no warnings

**What actually happened**: the batch-update API persists *only* the fields named in its field list. The new field was not in the list, so the in-memory assignment was silently discarded. Every record carried a `NULL` value for that field in production for the entire window between merge and detection.

**What caught it**: an explicit acceptance criterion — an e2e check asserting the field is populated on a real record after a real write, against a real datastore. No mocks, no in-memory state — just a query after the real system did real work.

**The general pattern**: this bug class is invisible at every layer below "did the real downstream system persist the right state." Many APIs expose a known silent-failure surface where a partial write drops data: a batch/bulk update with an explicit field list, a message-queue offset commit, a search-index mapping vs document mismatch, an event/signal vs bulk-insert path, a cascade-delete rule, a data-moving migration vs a schema-only one. AI-generated code threads these silently because the model optimizes for "the line looks reasonable," and the unit tests it writes never cross the boundary that drops the write.

**Implication for authoring acceptance criteria**: if a scenario touches one of these surfaces, the e2e/integration acceptance criterion is not optional. Naming the assertion explicitly — which field, on which record, after which operation — is what makes the test catch the bug instead of pass alongside it.
