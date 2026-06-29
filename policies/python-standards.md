# Python Coding Standards

> Apply these guidelines when writing new Python code or refactoring existing Python code
> in this QA framework (test design, automated regression, diagnostics tooling).

---

## Key Principles
- Prioritize readability over efficiency
- Use functional programming where appropriate; avoid unnecessary classes
- Use descriptive variable names that reflect the data they contain or their purpose (e.g., `is_active`, `has_permission`)
- Use descriptive function names
- Use the Receive an Object, Return an Object (RORO) pattern where it makes sense
- Keep functions under 10 statements
- Avoid introducing new global state; prefer dependency injection
- Avoid functions/methods with more than 5 parameters; group them when more are needed
- Code should read from top to bottom, with descriptive function and variable names

## Style and Syntax
- Target Python >=3.12
- Follow PEP 8 style guidelines with 120-character line limit
- Use `def` for pure functions and `async def` for asynchronous operations
- Do not write comments beyond docstrings unless complex design patterns or algorithms are used
- Use type hints for all function signatures; prefer `list` over `List` and `dict` over `Dict`
- Prefer Pydantic models over raw dictionaries for input validation (e.g., API request/response payloads, test fixtures, config objects)
- Avoid complex conditional logic in list comprehensions; avoid nested list comprehensions

## Tooling & Libraries
- Use `pyproject.toml` for project configuration
- Use the project's declared package manager consistently (e.g., `uv`, `poetry`, or `pip-tools`); do not mix managers within one project
- Use `ruff` for linting
- Use `pytest` for testing with `pytest-cov` for coverage
- Use Pydantic v2 for data modeling
- Create a Makefile with aliases for common operations (install, lint, test, run)

## Error Handling
- Validate inputs and preconditions at the beginning of functions
- Handle missing or malformed data appropriately (default, skip-with-flag, or fail-loud) and make the choice explicit
- Use try-except blocks for error-prone operations, especially when calling external systems (HTTP APIs, the system under test, message queues, browsers)
- Validate types and value ranges to ensure data integrity
- Handle errors and edge cases at the beginning of functions
- Use early returns for error conditions to avoid deeply nested `if` statements
- Place the happy path last in the function for improved readability
- Avoid unnecessary `else` statements; use the if-return pattern instead
- Use guard clauses to handle preconditions and invalid states early
- Implement proper error logging and user-friendly error messages; never log secrets or credentials
- Use custom error types or error factories for consistent error handling (e.g., distinguishing a product-under-test failure from a framework/infrastructure failure)

## Testing
- Place `tests/` at the same level as the files they test, or in the project's established test tree
- Leverage pytest markers declared in `pyproject.toml` (e.g., `unit`, `integration`, `e2e`, `slow`, `performance`) and apply them consistently
- Mark long-running or network-dependent flows so CI can route or exclude them and stay lean
- Maintain coverage by extending fixtures and factories in a shared `fixtures/` (or `tests/fixtures/`) location rather than duplicating setup
- Name tests with a clear, consistent convention (e.g., `test_<unit_under_test>.py` for unit tests and `test_<capability>.py` for integration tests)
- Test error handling and edge cases, not just the happy path
- Prioritize behavioral contracts (what the system does) over implementation-coupled tests (how it does it internally); a test that breaks on a refactor with no behavior change is a smell
- Use coverage as a diagnostic for gaps in critical paths, not as a target to maximize
- Prefer integration tests with real collaborators over heavily-mocked unit tests where practical — for a QA framework, a test that mocks the system under test verifies almost nothing

## Documentation
- Add a `README.md` explaining project architecture, plus install, lint, test, and run instructions

## Data Handling (when applicable)
- Use pandas for tabular data manipulation and analysis (e.g., aggregating test results or run metrics)
- Prefer method chaining for data transformations when it improves readability
- Use `loc` and `iloc` for explicit data selection
- Use `groupby` operations for efficient aggregation

## Visualization (when applicable)
- Use matplotlib for low-level plotting control and customization
- Use seaborn for statistical visualizations and pleasant defaults
- Create informative plots with proper labels, titles, and legends
- Use appropriate color schemes and consider color-blindness accessibility

## Performance Optimization
- Use vectorized operations in pandas and numpy instead of row-wise loops
- Use efficient data structures (e.g., categorical dtypes for low-cardinality string columns)
- Consider dask for larger-than-memory datasets
- Profile code to identify and optimize bottlenecks before optimizing speculatively
