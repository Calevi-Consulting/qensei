# BOOK-DUR — durable room persists with its baseline  · automated

REST regression (`existing_data`): find-or-creates a long-lived `qaf-keep:` room and verifies
it still holds its in-code baseline price on every later run — the durability/migration check.
Demonstrates the persona machinery (`keep_name`, `find_or_create`, the `is_protected_name`
no-delete guard) against the booker site, exactly as SHOP-DUR does against mock-shop. Against
the file-backed mock the room survives across boots, so the second run takes the "re-use, do
not recreate" path.

- Spec: [`sut/restful-booker/specs/BOOK-DUR-room-catalog.md`](../../specs/BOOK-DUR-room-catalog.md)
- Covers: `POST /room/`, `GET /room/`
- Tags: `durability`
- Run: `python3 -m engine.run --sut sut/restful-booker`
