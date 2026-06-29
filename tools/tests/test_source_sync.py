"""SUT source-provisioning tests — engine/source_sync.py.

The load-bearing case (TestSyncAgainstRealOrigin) exercises the real integration boundary:
it stands up an actual ``git`` origin repo on disk, clones it through ``sync()``, adds an
upstream commit, re-syncs, and then reads the freshly-synced ``ROUTES`` back through the
SUTConnector + design layers. No network — a local ``file://`` origin — so it runs in the
offline gate, but it is REAL git (clone/fetch/reset), not a mock. AI-plumbed provisioning can
pass every unit check yet fetch/reset the wrong tree because a SUT lives inside the parent
repo; only a booted clone-and-read catches that.

Run: ``python -m unittest discover -s tools/tests`` (or ``make test-engine``).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine import design, source_sync  # noqa: E402
from engine.sut import SUTConnector  # noqa: E402

MOCK_SHOP = str(ROOT / "sut" / "mock-shop")
BOOKER = str(ROOT / "sut" / "restful-booker")

APP_ONE_ROUTE = (
    "ROUTES = [('GET', '/widgets', 'list widgets')]\n"
    "BUSINESS_RULES = [{'id': 'w1', 'endpoint': '/widgets', 'description': 'lists widgets'}]\n"
)
APP_TWO_ROUTES = (
    "ROUTES = [('GET', '/widgets', 'list widgets'), ('POST', '/widgets', 'create a widget')]\n"
    "BUSINESS_RULES = [{'id': 'w1', 'endpoint': '/widgets', 'description': 'lists widgets'}]\n"
)


def _git(args, cwd):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True)


def _make_origin(tmp: Path, app_body: str) -> Path:
    """Create a real git origin repo (branch 'main') with an app.py at its root."""
    origin = tmp / "origin"
    origin.mkdir()
    _git(["init", "-q"], origin)
    _git(["checkout", "-q", "-b", "main"], origin)
    _git(["config", "user.email", "qa@example.com"], origin)
    _git(["config", "user.name", "QA"], origin)
    (origin / "app.py").write_text(app_body)
    _git(["add", "app.py"], origin)
    _git(["commit", "-q", "-m", "initial"], origin)
    return origin


def _write_sut(tmp: Path, source: dict) -> Path:
    sut = tmp / "sut"
    sut.mkdir()
    (sut / "manifest.json").write_text(json.dumps({
        "name": "provisioned-example",
        "source": source,
        "runtime": {"mode": "remote", "app": "app.py"},
    }))
    return sut


class TestSkipAndRefuse(unittest.TestCase):
    def test_no_repo_is_skip(self):
        with tempfile.TemporaryDirectory() as t:
            sut = _write_sut(Path(t), {"path": "source"})  # no repo -> in-repo source
            status, detail = source_sync.sync(str(sut))
            self.assertEqual(status, "SKIP", detail)

    def test_example_suts_skip(self):
        # The shipped example SUTs declare no source.repo — sync must be a safe no-op,
        # never touching their committed mock source.
        for sut in (MOCK_SHOP, BOOKER):
            status, _ = source_sync.sync(sut)
            self.assertEqual(status, "SKIP")

    def test_refuses_to_clobber_non_clone_source(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            origin = _make_origin(tmp, APP_ONE_ROUTE)
            sut = _write_sut(tmp, {"path": "source", "repo": origin.as_uri(), "ref": "main"})
            # A pre-existing, non-empty, non-git source dir must NOT be overwritten.
            (sut / "source").mkdir()
            (sut / "source" / "hand_written.py").write_text("# committed contract\n")
            status, detail = source_sync.sync(str(sut))
            self.assertEqual(status, "ERROR", detail)
            self.assertTrue((sut / "source" / "hand_written.py").exists(), "clobbered local source")


class TestSyncAgainstRealOrigin(unittest.TestCase):
    """Real git clone -> upstream commit -> re-sync fast-forwards -> design reads new ROUTES."""

    def test_clone_then_update_then_read(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            origin = _make_origin(tmp, APP_ONE_ROUTE)
            sut = _write_sut(tmp, {"path": "source", "repo": origin.as_uri(), "ref": "main", "depth": 1})

            # (1) Fresh clone.
            status, detail = source_sync.sync(str(sut))
            self.assertEqual(status, "SYNCED", detail)
            self.assertTrue((sut / "source" / "app.py").exists())
            src = SUTConnector(str(sut)).source_module()
            self.assertEqual([p for _, p, _ in src.ROUTES], ["/widgets"])

            # (2) Upstream advances; re-sync must fast-forward the worktree.
            (origin / "app.py").write_text(APP_TWO_ROUTES)
            _git(["commit", "-qam", "add create"], origin)
            status, detail = source_sync.sync(str(sut))
            self.assertEqual(status, "SYNCED", detail)

            # (3) design reads the freshly-synced surface (clone -> design path, end-to-end).
            conn = SUTConnector(str(sut))
            coverage = design.coverage(conn, str(conn.packs_dir))
            self.assertIn("POST /widgets", coverage["routes"])

    def test_idempotent_resync_no_change(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            origin = _make_origin(tmp, APP_ONE_ROUTE)
            sut = _write_sut(tmp, {"path": "source", "repo": origin.as_uri(), "ref": "main"})
            self.assertEqual(source_sync.sync(str(sut))[0], "SYNCED")
            head1 = source_sync._short_head(sut / "source")
            self.assertEqual(source_sync.sync(str(sut))[0], "SYNCED")
            head2 = source_sync._short_head(sut / "source")
            self.assertEqual(head1, head2)


if __name__ == "__main__":
    unittest.main()
