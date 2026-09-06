"""Machine-readable gate reports (JUnit XML / JSON) for CI rendering and triage.

The runner prints a human report; this emits a structured artifact a CI "Tests" tab or
triage tooling can consume (CI uploads it as a JUnit artifact). A result is
the tuple ``(case, expect, error, status)`` produced by the runner, where ``status`` is
one of ``PASS`` / ``FAIL`` / ``SKIP``.

**Provenance.** Every report declares whether the run had a fault **seeded** into the SUT
(``--seed-bug``, the framework's demo path for showing REAL_BUG detection). Without it a seeded red —
exit 1, a failing ``<testcase>``, everything a genuine regression produces — is byte-indistinguishable
from a real one in the artifact, so a triager handed the JUnit rather than the invocation has no way to
tell. The field is emitted on **every** report, ``false`` included: an absent marker would be ambiguous
between "not seeded" and "written by a version that did not say".
"""
from __future__ import annotations

import json
from xml.sax.saxutils import escape, quoteattr


def _failure_text(expect, error, skip_reason) -> str | None:
    if skip_reason:
        return None
    parts = [f.detail for f in (expect.failures if expect else [])]
    if error:
        parts.append(f"ERROR {error}")
    return "; ".join(parts) or None


def to_junit(results, suite_name="Qensei", seeded=False) -> str:
    """Render results as JUnit XML (one <testcase> per case; <skipped>/<failure> as needed).

    ``seeded`` records whether the run injected a fault into the SUT; it becomes a ``<property>`` so a
    consumer can tell a demo red from a genuine one."""
    n = len(results)
    failures = sum(1 for r in results if r[3] == "FAIL")
    skipped = sum(1 for r in results if r[3] == "SKIP")
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<testsuite name={quoteattr(suite_name)} tests="{n}" '
        f'failures="{failures}" skipped="{skipped}">',
        "  <properties>",
        f'    <property name="qensei.seeded" value="{str(bool(seeded)).lower()}"/>',
        "  </properties>",
    ]
    for case, expect, error, status in results:
        skip_reason = getattr(case, "_skip_reason", None) if status == "SKIP" else None
        name = quoteattr(f"{case.id} — {case.title}")
        lines.append(f'  <testcase classname={quoteattr(case.id)} name={name}>')
        if status == "SKIP":
            lines.append(f"    <skipped message={quoteattr(skip_reason or 'skipped')}/>")
        elif status == "FAIL":
            detail = _failure_text(expect, error, None) or "failed"
            lines.append(f'    <failure message={quoteattr(detail[:200])}>{escape(detail)}</failure>')
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    return "\n".join(lines)


def to_json(results, suite_name="Qensei", seeded=False) -> str:
    payload = {
        "suite": suite_name,
        "seeded": bool(seeded),
        "total": len(results),
        "passed": sum(1 for r in results if r[3] == "PASS"),
        "failed": sum(1 for r in results if r[3] == "FAIL"),
        "skipped": sum(1 for r in results if r[3] == "SKIP"),
        "cases": [
            {
                "id": case.id,
                "title": case.title,
                "persona": case.persona,
                "status": status,
                "detail": _failure_text(
                    expect, error, getattr(case, "_skip_reason", None) if status == "SKIP" else None
                )
                or (getattr(case, "_skip_reason", None) if status == "SKIP" else None),
            }
            for case, expect, error, status in results
        ],
    }
    return json.dumps(payload, indent=2)


def write_report(results, path: str, suite_name="Qensei", seeded=False) -> None:
    text = (
        to_junit(results, suite_name, seeded=seeded)
        if path.endswith(".xml")
        else to_json(results, suite_name, seeded=seeded)
    )
    from pathlib import Path

    Path(path).write_text(text)
