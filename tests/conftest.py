"""Shared pytest fixtures — per-worker SUT isolation for the site-pack bridge (test_sites.py).

This directory holds the **pytest** suite (the site-integration bridge). It is kept separate from
``tools/tests/`` — the zero-dependency ``unittest`` suite that ``make check`` / ``make test-engine``
run on the bare stdlib — because these modules import ``pytest``.

The framework's runtime is stateful: a SUT is one in-process server with a shared store, reset
between cases by ``run_case`` calling ``sut.isolate()``. To run the packs in PARALLEL under
pytest-xdist safely, each xdist worker must own its OWN server and its OWN durable-state files.
These fixtures provide exactly that: a per-worker state dir (xdist gives each worker its own
``tmp_path_factory`` basetemp) and a per-worker, per-site booted ``SUTConnector`` cache.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.sut import SUTConnector  # noqa: E402


@pytest.fixture(scope="session")
def _qaf_state_dir(tmp_path_factory):
    """A per-(xdist-worker) dir for the sites' durable-state files, so parallel workers never
    race on the file-backed stores (under xdist each worker has its own basetemp)."""
    return tmp_path_factory.mktemp("qaf-state")


@pytest.fixture(scope="session")
def _booted_suts(_qaf_state_dir):
    cache: dict[str, SUTConnector] = {}
    yield cache
    for sut in cache.values():
        sut.stop()


@pytest.fixture
def sut_for(_booted_suts, _qaf_state_dir):
    """Return a getter that boots (once per worker) and caches a ``SUTConnector`` per site,
    each with its own server + its own durable-state files."""
    def _get(site: str) -> SUTConnector:
        if site not in _booted_suts:
            # Set the per-worker state paths BEFORE the mock imports its source module on start().
            os.environ["QAF_MOCK_STATE"] = str(_qaf_state_dir / "mock-shop-accounts.json")
            os.environ["QAF_BOOKER_STATE"] = str(_qaf_state_dir / "booker-rooms.json")
            sut = SUTConnector(str(ROOT / site))
            sut.start()
            _booted_suts[site] = sut
        return _booted_suts[site]

    return _get
