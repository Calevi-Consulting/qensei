"""Personas & data durability — the machinery behind the persona labels.

A case declares a persona; this module is what makes the ``existing_data`` persona
mean something against a real, object-persisting backend (the mock is ephemeral, so
these helpers are exercised but dormant there).

  * ``new_user``     — creates ephemeral objects, self-cleans (see RegressionCase.teardown).
  * ``existing_data``— operates on long-lived objects via FIND-OR-CREATE: missing ⇒ create
                       from an in-code baseline; present ⇒ verify it persists with that
                       baseline (this is what catches DB-migration data loss).

Naming conventions (mirrors t-800 ``core/personas.py``):

  * ``keep_name(*parts)``      — stable, prefixed id for a durable object. NEVER deleted.
  * ``ephemeral_name(*parts)`` — unique id for a throwaway object, so a MISSED teardown
                                 leaves a harmless, findable, sweepable leftover.
  * ``is_protected_name(name)``— the no-delete guard any cleanup/sweep path must honour.

The prefixes are configurable per SUT (default ``qaf-keep:`` / ``qaf-ephemeral:``); the
helpers themselves are generic framework logic.
"""
from __future__ import annotations

import uuid

KEEP_PREFIX = "qaf-keep:"
EPHEMERAL_PREFIX = "qaf-ephemeral:"


def keep_name(*parts: str, prefix: str = KEEP_PREFIX) -> str:
    """A stable, idempotency-safe name for a durable (``existing_data``) object."""
    return prefix + ":".join(str(p) for p in parts)


def ephemeral_name(*parts: str, prefix: str = EPHEMERAL_PREFIX) -> str:
    """A unique name for a throwaway object (suffixed with a short uuid)."""
    tail = uuid.uuid4().hex[:8]
    return prefix + ":".join(str(p) for p in (*parts, tail))


def is_protected_name(name: str, prefix: str = KEEP_PREFIX) -> bool:
    """True if ``name`` is a durable keep object — cleanup MUST treat it as undeletable."""
    return isinstance(name, str) and name.startswith(prefix)


def find_or_create(find, create, name):
    """Generic find-or-create for a durable object.

    :param find:   ``callable(name) -> obj | None`` — look the object up by name.
    :param create: ``callable(name) -> obj`` — create it from the in-code baseline.
    :param name:   a :func:`keep_name`.
    :returns: ``(obj, created)`` — ``created`` is True only on the first run, so a case
        can assert the baseline on creation and assert PERSISTENCE on every later run.
    """
    found = find(name)
    if found is not None:
        return found, False
    return create(name), True
