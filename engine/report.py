"""Machine-readable gate reports (JUnit XML / JSON) for CI rendering and triage.

The runner prints a human report; this emits a structured artifact a CI "Tests" tab or
triage tooling can consume (t-800 uploads ``--junitxml`` as a CI artifact). A result is
the tuple ``(case, expect, error, status)`` produced by the runner, where ``status`` is
one of ``PASS`` / ``FAIL`` / ``SKIP``.
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


def to_junit(results, suite_name="qa-framework") -> str:
    """Render results as JUnit XML (one <testcase> per case; <skipped>/<failure> as needed)."""
    n = len(results)
    failures = sum(1 for r in results if r[3] == "FAIL")
    skipped = sum(1 for r in results if r[3] == "SKIP")
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<testsuite name={quoteattr(suite_name)} tests="{n}" '
        f'failures="{failures}" skipped="{skipped}">',
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


def to_json(results, suite_name="qa-framework") -> str:
    payload = {
        "suite": suite_name,
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


def write_report(results, path: str, suite_name="qa-framework") -> None:
    text = to_junit(results, suite_name) if path.endswith(".xml") else to_json(results, suite_name)
    from pathlib import Path

    Path(path).write_text(text)
