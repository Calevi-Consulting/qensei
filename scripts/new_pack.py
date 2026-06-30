"""Scaffold a new regression pack — ``python scripts/new_pack.py <TICKET> <slug>``.

Generates a self-contained, immediately-collectable pack from templates and refuses to
overwrite an existing one (an atomic claim, so parallel authors can't collide). Mirrors
t-800's ``scripts/new_pack.py`` so every pack starts consistent and discoverable.

  python scripts/new_pack.py SHOP-999 widget-restock     -> packs/SHOP-999-widget-restock/
  python scripts/new_pack.py noticket cart-currency      -> packs/noticket-cart-currency/
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASE_TEMPLATE = '''"""{pack_id} — {slug_human} ({persona}, REST)."""
from engine.case import RegressionCase


class {class_name}(RegressionCase):
    id = "{pack_id}"
    title = "{slug_human}"
    spec_ref = "core/specs/{pack_id}.md"
    persona = "new_user"          # or "existing_data"
    tags = frozenset({{"smoke"}})  # selection lane(s)
    severity = "medium"            # critical | high | medium | low
    requires = []                  # pre-flight requirement keys (see engine/preflight.py)
    covers = []                    # endpoints + business-rule ids (read by design)

    def run(self, sut, expect):
        status, body = sut.get("/")
        expect.is_not_none(body, "TODO: assert the behavioral contract")

    # def teardown(self, sut):     # new_user: delete what you created (best-effort)
    #     ...
'''

README_TEMPLATE = """# {pack_id} — {slug_human}  · spec'd

REST regression (`new_user`). TODO: one-paragraph index card — what contract it pins and why.

- Spec: [`core/specs/{pack_id}.md`](../../core/specs/{pack_id}.md)
- Covers: TODO
- Tags: `smoke`
- Run: `python3 -m engine.run --sut sut/mock-shop` (auto-discovered; filter a lane with `--select smoke`)
"""


def _class_name(slug: str) -> str:
    return "".join(w.capitalize() for w in re.split(r"[-_]", slug) if w) or "NewCase"


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    ticket, slug = argv
    if not re.fullmatch(r"[A-Za-z0-9]+(-[A-Za-z0-9]+)*|noticket", ticket):
        print(f"  bad ticket id {ticket!r} (use AP-123 / SHOP-9 / noticket)")
        return 2
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        print(f"  bad slug {slug!r} (use lower-kebab-case)")
        return 2

    pack_id = f"{ticket}-{slug}"
    pack_dir = ROOT / "packs" / pack_id
    if pack_dir.exists():  # atomic claim: never clobber an existing pack
        print(f"  pack {pack_id} already exists at {pack_dir} — refusing to overwrite")
        return 1

    slug_human = slug.replace("-", " ")
    fields = dict(pack_id=pack_id, slug=slug, slug_human=slug_human, persona="new_user",
                  class_name=_class_name(slug), pack_id_lower=pack_id)
    pack_dir.mkdir(parents=True)
    (pack_dir / "case.py").write_text(CASE_TEMPLATE.format(**fields))
    (pack_dir / "README.md").write_text(README_TEMPLATE.format(**fields))
    spec = ROOT / "core" / "specs" / f"{pack_id}.md"
    if not spec.exists():
        spec.write_text(f"# {pack_id} — {slug_human}\n\n## Status\n\nspec'd\n\n## Acceptance criteria\n\n- [ ] TODO\n")
    print(f"  created packs/{pack_id}/ (case.py + README.md) and core/specs/{pack_id}.md")
    print("  collect-check: python3 -m engine.run --sut sut/mock-shop  (the pack is auto-discovered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
