"""Tag-based test selection — run a subset of the suite by a marker expression.

Mature suites build CI lanes on a marker expression (e.g. ``pytest -m "<expr>"``). Here a
case declares ``tags = {"smoke", "slow", ...}`` and a small boolean-expression matcher
selects which cases run, so the gate can run lanes (smoke / slow / isolated / a domain)
instead of the whole SUT ``packs/`` directory.

Grammar (a safe subset, evaluated against the case's tag set):

    expr   := term (('and'|'or') term)*
    term   := 'not'? atom
    atom   := TAG | '(' expr ')'

``matches({"smoke"}, "smoke and not slow")`` → True. An empty/None expression matches
everything (run the whole suite). Only tag identifiers, the operators ``and/or/not`` and
parentheses are accepted — there is no ``eval`` of arbitrary input.
"""
from __future__ import annotations

import re

_TOKEN = re.compile(r"\s*(\(|\)|\band\b|\bor\b|\bnot\b|[A-Za-z_][A-Za-z0-9_-]*)\s*")


def _tokenize(expr: str) -> list[str]:
    tokens, pos = [], 0
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m:
            raise ValueError(f"bad token in selection expression at: {expr[pos:]!r}")
        tokens.append(m.group(1))
        pos = m.end()
    return tokens


def matches(tags, expr: str | None) -> bool:
    """True if the case's ``tags`` satisfy the selection ``expr`` (None ⇒ always)."""
    if not expr or not expr.strip():
        return True
    tokens = _tokenize(expr)
    tags = set(tags or ())
    pos = 0

    def parse_expr():
        nonlocal pos
        val = parse_term()
        while pos < len(tokens) and tokens[pos] in ("and", "or"):
            op = tokens[pos]
            pos += 1
            rhs = parse_term()
            val = (val and rhs) if op == "and" else (val or rhs)
        return val

    def parse_term():
        nonlocal pos
        if pos < len(tokens) and tokens[pos] == "not":
            pos += 1
            return not parse_term()
        return parse_atom()

    def parse_atom():
        nonlocal pos
        tok = tokens[pos]
        if tok == "(":
            pos += 1
            val = parse_expr()
            if pos >= len(tokens) or tokens[pos] != ")":
                raise ValueError("unbalanced parentheses in selection expression")
            pos += 1
            return val
        if tok in ("and", "or", ")"):
            raise ValueError(f"unexpected token {tok!r} in selection expression")
        pos += 1
        return tok in tags

    result = parse_expr()
    if pos != len(tokens):
        raise ValueError("trailing tokens in selection expression")
    return result
