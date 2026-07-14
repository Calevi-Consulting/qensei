"""Scaffold a new regression pack — ``python scripts/new_pack.py [--sut DIR] [--ui] <TICKET> <slug>``.

Generates a self-contained, immediately-collectable pack from templates and refuses to
overwrite an existing one (an atomic claim, so parallel authors can't collide), so every
pack starts consistent and immediately discoverable.

The pack and its spec land inside the TARGET SITE's self-contained subtree (a SUT plugin
owns its packs/specs), so ``--sut`` selects which site the regression belongs to. ``--ui``
scaffolds a browser-driven ``UICase`` into ``ui-packs/`` (Playwright) instead of the default
REST ``RegressionCase`` into ``packs/``:

  python scripts/new_pack.py SHOP-999 widget-restock
      -> sut/mock-shop/packs/SHOP-999-widget-restock/ + sut/mock-shop/specs/SHOP-999-widget-restock.md
  python scripts/new_pack.py --sut sut/restful-booker BOOK-9 cancel-booking
      -> sut/restful-booker/packs/BOOK-9-cancel-booking/ + sut/restful-booker/specs/BOOK-9-cancel-booking.md
  python scripts/new_pack.py --sut sut/restful-booker --ui BOOK-UI-9 cancel-flow
      -> sut/restful-booker/ui-packs/BOOK-UI-9-cancel-flow/ + sut/restful-booker/specs/BOOK-UI-9-cancel-flow.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASE_TEMPLATE = '''"""{pack_id} — {slug_human} ({persona}, REST)."""
from engine.case import RegressionCase


class {class_name}(RegressionCase):
    id = "{pack_id}"
    title = "{slug_human}"
    spec_ref = "{sut}/specs/{pack_id}.md"
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

- Spec: [`{sut}/specs/{pack_id}.md`](../../specs/{pack_id}.md)
- Covers: TODO
- Tags: `smoke`
- Run: `python3 -m engine.run --sut {sut}` (auto-discovered; filter a lane with `--select smoke`)
"""

UI_CASE_TEMPLATE = '''"""{pack_id} — {slug_human} ({persona}, Playwright UI)."""
from engine.ui import UICase


class {class_name}(UICase):
    id = "{pack_id}"
    title = "{slug_human}"
    spec_ref = "{sut}/specs/{pack_id}.md"
    persona = "new_user"          # or "existing_data"
    tags = frozenset({{"ui"}})     # UI packs run in the opt-in `ui` lane
    severity = "medium"            # critical | high | medium | low
    requires = []                  # pre-flight requirement keys (see engine/preflight.py)
    covers = []                    # UI + backend surface exercised (read by design)

    def run(self, page, base_url, expect):
        page.goto(base_url)
        # TODO: drive the site's UI (fill fields, click, wait) and assert the behavioral contract;
        # `page` is a Playwright Page. See sut/restful-booker/ui-packs/ for worked examples.
        expect.that(False, "TODO: assert the UI behavioral contract (replace this placeholder)")

    # def teardown(self, sut):     # new_user: delete what you created (best-effort)
    #     ...
'''

UI_README_TEMPLATE = """# {pack_id} — {slug_human}  · spec'd

Browser-driven UI regression (`UICase`, `new_user`, Playwright). TODO: one-paragraph index card —
what contract it pins and why.

- Spec: [`{sut}/specs/{pack_id}.md`](../../specs/{pack_id}.md)
- Covers: TODO
- Tags: `ui`
- Run (headless): `make test-ui`  ·  watch live: `make ui-watch`
"""


def _class_name(slug: str) -> str:
    return "".join(w.capitalize() for w in re.split(r"[-_]", slug) if w) or "NewCase"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="scaffold a new REST or UI regression pack inside a SUT plugin")
    ap.add_argument("--sut", default="sut/mock-shop", help="SUT plugin dir that owns the pack")
    ap.add_argument("--ui", action="store_true",
                    help="scaffold a browser-driven UICase into ui-packs/ (default: a REST RegressionCase into packs/)")
    ap.add_argument("ticket", help="ticket id (PROJ-123 / SHOP-9 / noticket)")
    ap.add_argument("slug", help="lower-kebab-case slug")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])
    ticket, slug = args.ticket, args.slug
    if not re.fullmatch(r"[A-Za-z0-9]+(-[A-Za-z0-9]+)*|noticket", ticket):
        print(f"  bad ticket id {ticket!r} (use PROJ-123 / SHOP-9 / noticket)")
        return 2
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        print(f"  bad slug {slug!r} (use lower-kebab-case)")
        return 2

    sut = args.sut.rstrip("/")
    sut_dir = ROOT / sut
    if not (sut_dir / "manifest.json").exists():
        print(f"  no SUT plugin at {sut} (expected a manifest.json there)")
        print(f"  create the plugin first:  make new-sut SUT={sut}   (see sut/contract.md § Adding a new SUT)")
        return 2

    subdir = "ui-packs" if args.ui else "packs"
    case_template = UI_CASE_TEMPLATE if args.ui else CASE_TEMPLATE
    readme_template = UI_README_TEMPLATE if args.ui else README_TEMPLATE

    pack_id = f"{ticket}-{slug}"
    pack_dir = sut_dir / subdir / pack_id
    if pack_dir.exists():  # atomic claim: never clobber an existing pack
        print(f"  pack {pack_id} already exists at {pack_dir} — refusing to overwrite")
        return 1

    slug_human = slug.replace("-", " ")
    fields = dict(pack_id=pack_id, slug=slug, slug_human=slug_human, persona="new_user",
                  class_name=_class_name(slug), sut=sut)
    pack_dir.mkdir(parents=True)
    (pack_dir / "case.py").write_text(case_template.format(**fields))
    (pack_dir / "README.md").write_text(readme_template.format(**fields))
    spec = sut_dir / "specs" / f"{pack_id}.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    if not spec.exists():
        spec.write_text(f"# {pack_id} — {slug_human}\n\n## Status\n\nspec'd\n\n## Acceptance criteria\n\n- [ ] TODO\n")
    print(f"  created {sut}/{subdir}/{pack_id}/ (case.py + README.md) and {sut}/specs/{pack_id}.md")
    if args.ui:
        print(f"  collect-check: QAF_SITES={sut} poetry run pytest tests/test_ui.py --collect-only"
              f"  (the UI pack is auto-discovered; run: make test-ui)")
    else:
        print(f"  collect-check: python3 -m engine.run --sut {sut}  (the pack is auto-discovered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
