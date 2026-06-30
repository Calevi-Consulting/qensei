"""SHOP-DUR — a durable account persists with its baseline across runs (existing_data).

This is the `existing_data` / data-durability persona: instead of creating throwaway
objects, it find-or-creates a LONG-LIVED account (a `qaf-keep:` name that cleanup must
never delete) and verifies it still holds its in-code baseline on every later run — the
check that catches DB-migration data loss. Against the file-backed mock store the account
genuinely survives across server boots, so a second `make test` run exercises the
"read-and-verify, do not recreate" path.
"""
from engine.case import RegressionCase
from engine.personas import find_or_create, is_protected_name, keep_name

ACCOUNT = keep_name("account", "durability-baseline")  # qaf-keep:account:durability-baseline
BASELINE_PLAN = "enterprise"


class AccountDurability(RegressionCase):
    id = "SHOP-DUR"
    title = "durable account persists with its baseline across runs"
    spec_ref = "sut/mock-shop/specs/SHOP-DUR-account-durability.md"
    persona = "existing_data"
    tags = frozenset({"durability"})
    severity = "high"
    covers = ["POST /accounts", "GET /accounts/{id}"]

    def run(self, sut, expect):
        def find(name):
            status, acct = sut.get(f"/accounts/{name}")
            return acct if status == 200 else None

        def create(name):
            status, acct = sut.post("/accounts", {"name": name, "plan": BASELINE_PLAN})
            expect.equal(status, 201, "durable account created on first run")
            return acct

        acct, created = find_or_create(find, create, ACCOUNT)

        # On every run — first (created) or later (re-read) — the baseline must hold.
        expect.is_not_none(acct, "durable account resolves")
        expect.equal(acct["name"], ACCOUNT, "durable account name persisted")
        expect.equal(acct["plan"], BASELINE_PLAN, "durable account baseline plan persisted")
        if not created:
            # A later run re-read the object instead of recreating it — the durability path.
            status, again = sut.post("/accounts", {"name": ACCOUNT, "plan": "downgraded"})
            expect.is_true(not again.get("created"), "find-or-create re-used the durable (did not recreate)")
            expect.equal(again["plan"], BASELINE_PLAN, "durable baseline NOT overwritten by a later run")

    def teardown(self, sut):
        # The no-delete guard: a durable (existing_data) object is NEVER deleted, even on teardown.
        if not is_protected_name(ACCOUNT):  # pragma: no cover - ACCOUNT is always protected
            sut.delete(f"/accounts/{ACCOUNT}")
