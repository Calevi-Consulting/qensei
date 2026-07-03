"""WIDGET-1 — a created widget starts active (new_user, REST). Sourceless-SUT demo pack."""
from engine.case import RegressionCase


class CreatedWidgetIsActive(RegressionCase):
    id = "WIDGET-1"
    title = "a created widget starts active"
    spec_ref = "sut/widget-api/specs/WIDGET-1-create-widget.md"
    persona = "new_user"
    tags = frozenset({"smoke"})
    severity = "high"
    covers = ["POST /widgets", "GET /widgets/{id}"]
    # The contract of record is the TICKET (this SUT is sourceless — no BUSINESS_RULES to read).
    # diagnostics returns INDETERMINATE for a failure here; the ticket says a new widget is "active".
    contract_claim = {"rule": "widget-starts-active", "status": "active"}

    def run(self, sut, expect):
        status, w = sut.post("/widgets", {"name": "qaf-ephemeral-demo"})
        expect.equal(status, 201, "create widget status")
        expect.is_not_none(w, "created widget body")
        expect.equal(w["status"], "active", "new widget starts active")

        wid = w["id"]
        status, got = sut.get(f"/widgets/{wid}")
        expect.equal(status, 200, "GET widget status")
        expect.equal(got["status"], "active", "widget still active on read")

    def teardown(self, sut):
        # The stub runtime is ephemeral (in-memory, reset on each boot), so a new_user case
        # leaves nothing durable behind. A real widget service would DELETE /widgets/{id} here.
        return None
