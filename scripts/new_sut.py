"""Scaffold a new SUT plugin — ``python scripts/new_sut.py <sut/dir> [--sourceless]``.

Stands up the minimal plugin skeleton so an adopter wraps THEIR product without touching ``engine/``
or ``policies/``. The engine, gates, and the CI / pytest site matrices auto-discover it
(see ``engine/sites.py``). You then fill the manifest (base_url + creds), point ``source`` at your
backend (or go sourceless), and add packs with ``make new-pack SUT=<dir> TICKET=... SLUG=...``.

The skeleton uses a **remote** runtime (a real backend reached over the network) — the common adopter
case; the shipped ``sut/mock-shop`` / ``sut/restful-booker`` are in-process *mocks* for the demo. A
remote SUT is excluded from the default OFFLINE gate until you configure creds/env (run it with
``QAF_SITES=<dir>``); a `mock-shop`-style in-process mock is the worked example to copy for that.

  python scripts/new_sut.py sut/acme               # sourced: design reads source/ ROUTES + BUSINESS_RULES
  python scripts/new_sut.py sut/acme --sourceless  # no readable source; the ticket is the contract
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE_STUB = '''"""TODO: replace with (or point manifest source.repo at) YOUR backend's contract surface.

design.py + diagnostics.py read ROUTES + BUSINESS_RULES from here. For a real backend, set the
manifest ``source.repo`` (+ ``ref``), gitignore this dir, and ``make sync-source SUT=<dir>`` to
clone/refresh it before design/diagnostics read it.
"""
ROUTES = [
    # (METHOD, path_template, description) — the endpoints your packs' `covers` resolve against.
    # ("GET", "/widgets/{id}", "fetch a widget"),
]
BUSINESS_RULES = [
    # {"id": "rule-id", ...} — the contract values diagnose classifies REAL_BUG vs TEST_BUG against.
    # {"id": "widget-starts-active"},
]
'''

README = """# {name} — SUT plugin

TODO: one paragraph — what product this wraps and how it is reached.

- Runtime: `remote` — set `QAF_BASE_URL` / `QAF_TOKEN` via env / `.env` (never commit creds).{source_line}
- Add a pack: `make new-pack SUT={sut} TICKET=<T> SLUG=<slug>`
- Run its gate: `QAF_SITES={sut} make test SUT={sut}`

Auto-discovered — no edits to `engine/`, the CI matrix, or the pytest bridges are needed
(`engine/sites.py`). A `remote` SUT joins the default offline gate only once it is `in_process`
or you run it explicitly with creds configured.
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="scaffold a new SUT plugin skeleton")
    ap.add_argument("sut", help="the plugin dir, e.g. sut/acme")
    ap.add_argument("--sourceless", action="store_true",
                    help="no readable backend source (runtime remote; the ticket is the contract)")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    sut = args.sut.rstrip("/")
    if not re.fullmatch(r"sut/[a-z0-9]+(-[a-z0-9]+)*", sut):
        print(f"  bad SUT dir {sut!r} (use sut/<lower-kebab-name>, e.g. sut/acme)")
        return 2
    name = sut.split("/", 1)[1]
    sut_dir = ROOT / sut
    if sut_dir.exists():
        print(f"  {sut} already exists — refusing to overwrite")
        return 1

    dirs = ["packs", "specs", "tickets", "skills", "learnings"] + ([] if args.sourceless else ["source"])
    for d in dirs:
        (sut_dir / d).mkdir(parents=True, exist_ok=True)
        (sut_dir / d / ".gitkeep").write_text("")  # keep the empty dir committable

    manifest: dict = {"name": name, "description": f"TODO: {name} backend under test."}
    if not args.sourceless:
        manifest["source"] = {"path": "source",
                              "note": "point at a clone of your backend; set source.repo for `make sync-source`"}
    manifest["runtime"] = {"mode": "remote", "base_url": "https://TODO.example.com",
                           "note": "Real backend. Override base_url/creds via QAF_* env / .env — never commit them."}
    manifest["env"] = {"local": {"base_url": "https://TODO.example.com"}}
    manifest["creds"] = {"mode": "token", "note": "Resolve QAF_TOKEN via env/Vault; see engine/credentials.py."}
    manifest["knowledge"] = {"skills": "skills", "learnings": "learnings"}
    (sut_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    if not args.sourceless:
        (sut_dir / "source" / "app.py").write_text(SOURCE_STUB)
    source_line = "" if args.sourceless else (
        "\n- Source: fill `source/app.py` (or set `source.repo`) with your ROUTES + BUSINESS_RULES.")
    (sut_dir / "README.md").write_text(README.format(name=name, sut=sut, source_line=source_line))

    kind = "sourceless" if args.sourceless else "sourced"
    extra = "" if args.sourceless else "source/app.py + "
    print(f"  created {sut}/ ({kind}): manifest.json + {extra}packs/ specs/ tickets/ skills/ learnings/")
    print(f"  next: set QAF_BASE_URL / QAF_TOKEN, then  make new-pack SUT={sut} TICKET=<T> SLUG=<slug>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
