r"""Shared mechanics of the two record lints — ``design_panel_lint`` (Phase 2b) and
``panel_section_lint`` (Phase 4).

The two lints gate different artifacts at different phases and keep their own contracts; what they
share is the part that must behave identically or the record format silently diverges:

* **section scoping** — an entry counts only inside its section, from the header to the next header
  of the same or a higher level (a sub-header inside the section does not end it);
* **noise stripping** — fenced code (``\`\`\``` or ``~~~``) and HTML comments are removed first, so a
  pasted example or guidance text never satisfies a record, and a ``# …`` line inside a fence is not
  mistaken for a header. Fences go first: a ``<!--`` inside a fence must not pair with a real ``-->``;
* **changed-file scoping** — ``--changed [--base REF]`` lets a lint compute its own file list with
  ``git … -z`` (spaces and non-ASCII survive) instead of a shell pipe that turns a git error into a
  silent "clean". A git failure is exit ``2`` (the repo's false-green-guard convention), never a pass;
* **reading** — a path that cannot be read or decoded is a lint failure line, not a traceback, and
  the rest of the batch is still checked.
"""
from __future__ import annotations

import re
import subprocess

EXIT_OK, EXIT_FAIL, EXIT_GUARD = 0, 1, 2

FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def strip_noise(text: str) -> str:
    """Remove fenced code (first) and HTML comments (second)."""
    return COMMENT_RE.sub("", FENCE_RE.sub("", text))


def section_body(text: str, header_re: re.Pattern[str]) -> str | None:
    """The text after the first ``header_re`` match, up to the next markdown header of the same or a
    higher level; ``None`` when the section is absent. ``header_re`` must capture the hashes as ``h``."""
    text = strip_noise(text)
    m = header_re.search(text)
    if m is None:
        return None
    level = len(m.group("h"))
    end_re = re.compile(rf"(?m)^#{{1,{level}}}(?!#)(?:[ \t]|$)")
    rest = text[m.end():]
    nxt = end_re.search(rest)
    return rest[: nxt.start()] if nxt else rest


def changed_files(pathspecs: list[str], base: str | None = None) -> list[str] | None:
    """Paths matching ``pathspecs`` that differ from ``base`` (default ``HEAD``) plus untracked ones,
    NUL-delimited so odd names survive; ``None`` when git cannot answer (caller exits 2)."""
    cmds = (
        ["git", "-c", "core.quotePath=false", "diff", "--name-only", "-z", base or "HEAD", "--", *pathspecs],
        ["git", "-c", "core.quotePath=false", "ls-files", "--others", "--exclude-standard", "-z", "--", *pathspecs],
    )
    raw = b""
    for cmd in cmds:
        try:
            raw += subprocess.run(cmd, check=True, capture_output=True).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    return sorted({p for p in raw.decode("utf-8", "surrogateescape").split("\0") if p})


def read_text(path: str) -> tuple[str | None, str | None]:
    """``(text, None)`` on success; ``(None, None)`` when the file is gone (deleted in this change);
    ``(None, reason)`` when it exists but cannot be read as UTF-8 text."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read(), None
    except FileNotFoundError:
        return None, None
    except (OSError, UnicodeDecodeError) as e:
        return None, f"{type(e).__name__}: {e}"


def lint_paths(paths, *, is_lintable, check_text, tag: str, name: str, epilogue: str) -> int:
    """Run ``check_text`` over every lintable path; print one ``[tag]`` line per failure."""
    failures: list[str] = []
    for path in paths:
        if not is_lintable(path):
            continue
        text, err = read_text(path)
        if err:
            failures.append(f"  [{tag}] {path} — unreadable ({err})")
            continue
        if text is None:
            continue  # deleted in this change — nothing left to record
        reason = check_text(text)
        if reason:
            failures.append(f"  [{tag}] {path} — {reason}")
    if failures:
        print("\n".join(failures))
        print(f"\n  {name}: {epilogue}")
        return EXIT_FAIL
    print(f"  {name}: clean")
    return EXIT_OK


def resolve_paths(args, pathspecs: list[str], name: str) -> tuple[list[str] | None, int]:
    """Explicit paths, or the changed set under ``--changed``; ``(None, 2)`` when git cannot answer."""
    if not args.changed:
        return list(args.paths), EXIT_OK
    files = changed_files(pathspecs, args.base)
    if files is None:
        print(f"  {name}: could not determine the changed files (git failed) — refusing to report clean.")
        return None, EXIT_GUARD
    return files, EXIT_OK
