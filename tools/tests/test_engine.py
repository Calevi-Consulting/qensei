"""Unit tests for the engine core. Pure stdlib unittest.

Run: ``python -m unittest discover -s tools/tests`` (or ``make test-engine``).
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine import credentials, fidelity_lint, masking, personas, selection  # noqa: E402
from engine.case import Expect, PreconditionError, RegressionCase  # noqa: E402
from engine.citation_gate import resolve_citations  # noqa: E402
from engine.config import Settings  # noqa: E402
from engine.preflight import Registry, Unmet, evaluate  # noqa: E402
from engine.report import to_json, to_junit  # noqa: E402


class TestSelection(unittest.TestCase):
    def test_empty_matches_all(self):
        self.assertTrue(selection.matches({"smoke"}, None))
        self.assertTrue(selection.matches(set(), ""))

    def test_and_or_not(self):
        self.assertTrue(selection.matches({"smoke"}, "smoke and not slow"))
        self.assertFalse(selection.matches({"smoke", "slow"}, "smoke and not slow"))
        self.assertTrue(selection.matches({"slow"}, "smoke or slow"))
        self.assertTrue(selection.matches({"a"}, "(a or b) and not c"))

    def test_bad_token_raises(self):
        with self.assertRaises(ValueError):
            selection.matches({"a"}, "a &&& b")


class TestPersonas(unittest.TestCase):
    def test_keep_and_protected(self):
        n = personas.keep_name("account", "baseline")
        self.assertEqual(n, "qaf-keep:account:baseline")
        self.assertTrue(personas.is_protected_name(n))
        self.assertFalse(personas.is_protected_name("qaf-ephemeral:x"))

    def test_ephemeral_unique(self):
        a, b = personas.ephemeral_name("conn"), personas.ephemeral_name("conn")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("qaf-ephemeral:conn:"))

    def test_find_or_create(self):
        store = {}
        obj, created = personas.find_or_create(store.get, lambda n: store.setdefault(n, {"n": n}), "k")
        self.assertTrue(created)
        obj2, created2 = personas.find_or_create(store.get, lambda n: 1 / 0, "k")
        self.assertFalse(created2)
        self.assertEqual(obj, obj2)


class TestMasking(unittest.TestCase):
    def test_deep_mask(self):
        m = masking.mask({"Authorization": "Bearer x", "body": {"password": "p", "ok": 1}, "list": [{"token": "t"}]})
        self.assertEqual(m["Authorization"], masking.REDACTED)
        self.assertEqual(m["body"]["password"], masking.REDACTED)
        self.assertEqual(m["body"]["ok"], 1)
        self.assertEqual(m["list"][0]["token"], masking.REDACTED)

    def test_scalars_passthrough(self):
        self.assertEqual(masking.mask("plain"), "plain")
        self.assertIsNone(masking.mask(None))


class TestCredentials(unittest.TestCase):
    def test_none(self):
        self.assertEqual(credentials.resolve_auth_headers({"mode": "none"}, Settings()), {})

    def test_token(self):
        h = credentials.resolve_auth_headers({"mode": "token"}, Settings(token="abc"))
        self.assertEqual(h, {"Authorization": "Bearer abc"})

    def test_token_missing_raises(self):
        with self.assertRaises(credentials.CredentialError):
            credentials.resolve_auth_headers({"mode": "token"}, Settings())

    def test_userpass(self):
        h = credentials.resolve_auth_headers({"mode": "userpass"}, Settings(username="u", password="p"))
        self.assertTrue(h["Authorization"].startswith("Basic "))

    def test_provider(self):
        prov = lambda s: {"headers": {"X-Api-Key": "k"}}
        h = credentials.resolve_auth_headers({"mode": "provider"}, Settings(), provider=prov)
        self.assertEqual(h, {"X-Api-Key": "k"})

    def test_provider_missing_raises(self):
        with self.assertRaises(credentials.CredentialError):
            credentials.resolve_auth_headers({"mode": "provider"}, Settings())


class TestConfig(unittest.TestCase):
    def test_dotenv_then_env_then_override(self):
        with tempfile.TemporaryDirectory() as d:
            dotenv = Path(d) / ".env"
            dotenv.write_text('QAF_ENV=staging\nQAF_TOKEN="from-dotenv"\n# comment\n')
            os.environ["QAF_TOKEN"] = "from-env"
            try:
                s = Settings.load(dotenv=dotenv, overrides={"BASE_URL": "https://x"})
                self.assertEqual(s.env, "staging")  # from .env
                self.assertEqual(s.token, "from-env")  # env wins over .env
                self.assertEqual(s.base_url, "https://x")  # override wins
            finally:
                del os.environ["QAF_TOKEN"]

    def test_verify_tls_flag(self):
        self.assertFalse(Settings.load(overrides={"VERIFY_TLS": "0"}).verify_tls)
        self.assertTrue(Settings.load().verify_tls)


class TestPreflight(unittest.TestCase):
    def test_collision_guard(self):
        reg = Registry()
        reg.register("k", lambda sut: True)
        with self.assertRaises(ValueError):
            reg.register("k", lambda sut: True)

    def test_evaluate_skip_and_unknown(self):
        reg = Registry()
        reg.register("present", lambda sut: True)
        reg.register("absent", lambda sut: False)

        class C(RegressionCase):
            requires = ["present", "absent", "never_registered"]

        unmet = evaluate(C, sut=None, registry=reg)
        keys = {u.key for u in unmet}
        self.assertEqual(keys, {"absent", "never_registered"})
        self.assertTrue(all(isinstance(u, Unmet) for u in unmet))

    def test_check_that_raises_is_unmet(self):
        reg = Registry()
        reg.register("boom", lambda sut: 1 / 0)

        class C(RegressionCase):
            requires = ["boom"]

        unmet = evaluate(C, sut=None, registry=reg)
        self.assertEqual(len(unmet), 1)
        self.assertIn("raised", unmet[0].reason)


class TestExpect(unittest.TestCase):
    def test_matchers(self):
        e = Expect()
        e.equal(1, 1, "eq")
        e.not_equal(1, 2, "ne")
        e.contains([1, 2], 2, "in")
        e.is_none(None, "none")
        e.is_not_none(5, "notnone")
        e.is_true(1, "truthy")
        self.assertTrue(e.passed)
        e.equal(1, 2, "fail")
        self.assertFalse(e.passed)
        self.assertEqual(len(e.failures), 1)

    def test_precondition_raises(self):
        e = Expect()
        with self.assertRaises(PreconditionError):
            e.precondition(False, "must hold")


class TestReport(unittest.TestCase):
    def _results(self):
        class C(RegressionCase):
            id, title, persona = "C-1", "t", "new_user"

        e = Expect()
        e.equal(1, 2, "boom")
        skipped = C()
        skipped._skip_reason = "no creds"
        return [(C(), e, None, "FAIL"), (C(), Expect(), None, "PASS"), (skipped, Expect(), None, "SKIP")]

    def test_junit(self):
        xml = to_junit(self._results(), "suite")
        self.assertIn('tests="3"', xml)
        self.assertIn('failures="1"', xml)
        self.assertIn("<skipped", xml)
        self.assertIn("<failure", xml)

    def test_json(self):
        import json

        data = json.loads(to_json(self._results()))
        self.assertEqual((data["passed"], data["failed"], data["skipped"]), (1, 1, 1))


class TestCitationGate(unittest.TestCase):
    def test_ok_fabricated_unverifiable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "sut" / "mock" / "source"
            src.mkdir(parents=True)
            (src / "app.py").write_text("line1\nline2\nline3\n")
            cites = resolve_citations(
                "see sut/mock/source/app.py:2 and sut/mock/source/app.py:99 and sut/ghost/source/x.py:1",
                repo_root=str(root),
            )
            by = {c.raw.rsplit("/", 1)[-1]: c.status for c in cites}
            self.assertEqual(by["app.py:2"], "OK")
            self.assertEqual(by["app.py:99"], "FABRICATED")
            self.assertEqual(by["x.py:1"], "UNVERIFIABLE")


class TestFidelityLint(unittest.TestCase):
    BASE = '''
from engine.case import RegressionCase
class Case(RegressionCase):
    id = "X-1"
    persona = "existing_data"
    severity = "high"
    tags = frozenset({"smoke", "slow"})
    def run(self, sut, expect):
        expect.equal(1, 1, "a")
        expect.equal(2, 2, "b")
'''

    def _lint(self, current_src, base_src=BASE, allow_reshape=False):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "case.py"
            p.write_text(current_src)
            orig = fidelity_lint._git_base
            fidelity_lint._git_base = lambda path, ref: base_src
            try:
                return fidelity_lint.lint_file(str(p), allow_reshape=allow_reshape)
            finally:
                fidelity_lint._git_base = orig

    def test_clean_when_identical(self):
        self.assertEqual(self._lint(self.BASE), [])

    def test_persona_weakening(self):
        weak = self.BASE.replace('persona = "existing_data"', 'persona = "new_user"')
        rules = {f.rule for f in self._lint(weak)}
        self.assertIn("persona-changed", rules)

    def test_severity_downgrade_and_shrink_and_fewer_asserts(self):
        weak = (
            self.BASE.replace('severity = "high"', 'severity = "low"')
            .replace('frozenset({"smoke", "slow"})', 'frozenset({"smoke"})')
            .replace('        expect.equal(2, 2, "b")\n', "")
        )
        rules = {f.rule for f in self._lint(weak)}
        self.assertIn("severity-downgraded", rules)
        self.assertIn("tags-shrank", rules)
        self.assertIn("assertions-removed", rules)

    def test_case_removed(self):
        rules = {f.rule for f in self._lint("x = 1\n")}
        self.assertIn("case-removed", rules)

    def test_new_file_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "case.py"
            p.write_text(self.BASE)
            orig = fidelity_lint._git_base
            fidelity_lint._git_base = lambda path, ref: None  # no baseline
            try:
                self.assertEqual(fidelity_lint.lint_file(str(p)), [])
            finally:
                fidelity_lint._git_base = orig

    def test_allow_reshape_downgrades_shrink(self):
        weak = self.BASE.replace('frozenset({"smoke", "slow"})', 'frozenset({"smoke"})')
        sev = {f.rule: f.severity for f in self._lint(weak, allow_reshape=True)}
        self.assertEqual(sev["tags-shrank"], "warn")


if __name__ == "__main__":
    unittest.main()
