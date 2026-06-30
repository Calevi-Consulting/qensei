"""Pre-flight requirements — declare per-case prerequisites; skip-or-block on the target.

A case targeting several environments cannot assume every backend has the data/features
it needs. It declares prerequisites with ``requires = [...]``; before running, the engine
resolves each key against the TARGET backend and either:

  * ``partial`` (default) — SKIP a case with an unmet requirement (the rest still run), or
  * ``block``             — FAIL it (use when every prerequisite MUST hold).

The specific checks are plugin-supplied (a real ``sut/aiq`` plugin answers "is connector
X deployed on this env?"); the engine owns the registry + the skip/block policy. This is
the product-neutral half of t-800's ``core/preflight.py`` + ``core/requirements.py``.

A plugin registers checks from ``sut/<name>/plugin.py`` by defining::

    REQUIREMENTS = {"catalog_seeded": lambda sut: sut.get("/products")[0] == 200}

The framework always provides ``platform_reachable`` (the SUT answered a probe).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Unmet:
    key: str
    reason: str


class Registry:
    """A namespaced map of requirement-key -> ``check(sut) -> bool``.

    Duplicate registration of the same key raises (mirrors t-800's collision guard) so a
    plugin cannot silently shadow a built-in or another plugin's check.
    """

    def __init__(self):
        self._checks: dict[str, callable] = {}

    def register(self, key: str, check) -> None:
        if key in self._checks:
            raise ValueError(f"requirement key {key!r} already registered (collision)")
        self._checks[key] = check

    def update(self, mapping: dict) -> None:
        for key, check in (mapping or {}).items():
            self.register(key, check)

    def __contains__(self, key):
        return key in self._checks

    def check(self, key: str, sut) -> bool:
        if key not in self._checks:
            raise KeyError(f"unknown requirement {key!r} (not registered by the engine or plugin)")
        return bool(self._checks[key](sut))


def default_registry(sut) -> Registry:
    """A registry seeded with the always-available checks + the plugin's REQUIREMENTS."""
    reg = Registry()
    reg.register("platform_reachable", _platform_reachable)
    plugin_reqs = getattr(sut.plugin(), "REQUIREMENTS", None) if sut.plugin() else None
    if plugin_reqs:
        reg.update(plugin_reqs)
    return reg


def _platform_reachable(sut) -> bool:
    try:
        status, _ = sut.get("/")
        return status < 500
    except Exception:
        return False


def evaluate(case, sut, registry: Registry) -> list[Unmet]:
    """Return the unmet requirements of ``case`` against ``sut`` (empty ⇒ all satisfied)."""
    unmet: list[Unmet] = []
    for key in getattr(case, "requires", []) or []:
        if key not in registry:
            unmet.append(Unmet(key, "requirement not registered by the engine or plugin"))
            continue
        try:
            if not registry.check(key, sut):
                unmet.append(Unmet(key, "check returned False on the target environment"))
        except Exception as e:  # a check that errors is treated as unmet, not a crash
            unmet.append(Unmet(key, f"check raised: {e!r}"))
    return unmet
