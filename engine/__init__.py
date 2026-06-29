"""qa-framework engine — the generic QA core.

A backend-aware hybrid of test-case DESIGN (read the backend, propose cases),
automated REGRESSION (run cases against a live system — the gate), and
DIAGNOSTICS (classify a failure as REAL_BUG vs TEST_BUG by reading the backend
contract). Domain-agnostic: it talks to any System Under Test through a plugin
under sut/<name>/ (see sut/contract.md).
"""

__version__ = "0.0.1"
