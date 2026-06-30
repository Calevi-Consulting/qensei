"""BOOK-DUR — a durable room persists with its baseline across runs (existing_data, REST).

The `existing_data` / data-durability persona for the booker site: instead of creating
throwaway objects, it find-or-creates a LONG-LIVED room (a `qaf-keep:` name cleanup must
never delete) and verifies it still holds its in-code baseline price on every later run — the
check that catches catalog/migration data loss. Against the file-backed mock store the room
genuinely survives across server boots, so a second run exercises the "read-and-verify, do
not recreate" path. Mirrors mock-shop's SHOP-DUR, proving the persona machinery is generic.
"""
from engine.case import RegressionCase
from engine.personas import find_or_create, is_protected_name, keep_name

ROOM = keep_name("room", "durability-baseline")  # qaf-keep:room:durability-baseline
BASELINE_PRICE = 250


class RoomCatalogDurability(RegressionCase):
    id = "BOOK-DUR"
    title = "durable room persists with its baseline price across runs"
    spec_ref = "sut/restful-booker/specs/BOOK-DUR-room-catalog.md"
    persona = "existing_data"
    tags = frozenset({"durability"})
    severity = "high"
    requires = ["rooms_available"]
    covers = ["POST /room/", "GET /room/"]

    def run(self, sut, expect):
        def find(name):
            status, body = sut.get("/room/")
            if status != 200:
                return None
            return next((r for r in (body or {}).get("rooms", []) if r["roomName"] == name), None)

        def create(name):
            status, room = sut.post("/room/", {
                "roomName": name, "type": "Suite", "roomPrice": BASELINE_PRICE,
                "description": "durability baseline room",
            })
            expect.equal(status, 201, "durable room created on first run")
            return room

        room, created = find_or_create(find, create, ROOM)

        # On every run — first (created) or later (re-read) — the baseline must hold.
        expect.is_not_none(room, "durable room resolves")
        expect.equal(room["roomName"], ROOM, "durable room name persisted")
        expect.equal(room["roomPrice"], BASELINE_PRICE, "durable room baseline price persisted")
        if not created:
            # A later run re-read the room instead of recreating it — the durability path.
            status, again = sut.post("/room/", {"roomName": ROOM, "type": "Suite", "roomPrice": 999})
            expect.is_true(not again.get("created"), "find-or-create re-used the durable (did not recreate)")
            expect.equal(again["roomPrice"], BASELINE_PRICE, "durable baseline NOT overwritten by a later run")

    def teardown(self, sut):
        # The no-delete guard: a durable (existing_data) object is NEVER deleted, even on teardown.
        if not is_protected_name(ROOM):  # pragma: no cover - ROOM is always protected
            sut.delete(f"/room/{ROOM}")
