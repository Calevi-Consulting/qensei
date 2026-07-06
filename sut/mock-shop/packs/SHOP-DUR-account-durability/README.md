# SHOP-DUR — durable account persists with its baseline  · automated

REST regression (`existing_data`): find-or-creates a long-lived `qaf-keep:` account and
verifies it still holds its in-code baseline on every later run — the durability/migration
check. Demonstrates the persona machinery: `keep_name` (stable protected id), `find_or_create`
(create on first run, read-and-verify after), and `is_protected_name` (the no-delete guard the
`teardown` honours — a durable is never deleted). Against the file-backed mock store the account
survives across boots, so the second run takes the "re-use, do not recreate" path.

- Spec: [`sut/mock-shop/specs/SHOP-DUR-account-durability.md`](../../specs/SHOP-DUR-account-durability.md)
- Covers: `POST /accounts`, `GET /accounts/{name}`
- Tags: `durability`
- Run: `python3 -m engine.run --sut sut/mock-shop`
