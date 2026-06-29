"""SUTConnector — the generic "backend access" abstraction.

This is the seam that makes the framework domain-agnostic. A System Under Test
plugin (a directory under sut/<name>/) declares, in manifest.json:

  * runtime : how to reach the RUNNING system
              - {"mode": "in_process", "app": "app.py", "factory": "make_server"}
                (the mock: the framework boots the backend in-process)
              - {"mode": "remote", "base_url": "https://..."}   (a real backend)
              - optional "isolate": a path POSTed before each case for a clean state,
                and "verify_tls": false for self-signed onprem certs
  * source  : where the backend SOURCE lives (read by design + diagnostics). A real SUT may add
              {"repo", "ref", "depth"} so engine/source_sync.py clones/refreshes it locally.
  * tests   : the plugin's OWN test assets, so each site is self-contained and the gate
              for one site never runs another's: {"packs", "specs", "tickets", "ui_packs"}
              (relative to sut/<name>/; default packs/specs/tickets/ui-packs). run.py /
              design.py default --packs to this plugin's packs_dir; ui_packs holds the
              browser-driven UICase packs (engine/ui.py).
  * ui      : {"path": "/ui"} — where the site serves its WEB UI (relative to base_url).
              Present ⇒ the site has a UI testing surface the Playwright lane drives; absent
              ⇒ REST-only.
  * env     : named environments -> {"base_url": ...} (selected with --env / QAF_ENV)
  * creds   : credential resolution (none | token | userpass | provider) — see credentials.py
              (overridable per-run with QAF_CREDS_MODE, e.g. flip a mock's "none" to
              "provider" to log in against the same plugin's real "live" env)
  * knowledge: skills + learnings dirs (domain manual-QA context)

A plugin MAY ship an optional ``plugin.py`` exposing hooks the engine calls when present
(none required by the mock): ``REQUIREMENTS`` (pre-flight checks), ``resolve_creds(settings)``
(Vault/AWS-SM provider), ``isolate(sut)`` (custom clean-state reset), ``sweep(sut, max_age,
dry_run)`` (orphan reaper). This is how product-specific behaviour plugs in WITHOUT editing core.

Both things the framework needs — calling the live API AND reading the backend source —
go through this one object.
"""
from __future__ import annotations

import importlib.util
import json
import ssl
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from engine.config import Settings
from engine.credentials import resolve_auth_headers
from engine.masking import mask

# Transient gateway statuses worth retrying. Writes only retry 502/503 (NOT 504): a 504 on
# a POST may mean the create succeeded server-side, so retrying could duplicate it.
_RETRY_GET = frozenset({502, 503, 504})
_RETRY_WRITE = frozenset({502, 503})
_RETRY_ATTEMPTS = 3
_BACKOFF_BASE = 0.2


class SUTConnector:
    def __init__(self, sut_dir, settings: Settings | None = None):
        self.dir = Path(sut_dir).resolve()
        self.manifest = json.loads((self.dir / "manifest.json").read_text())
        self.name = self.manifest["name"]
        self.source_dir = self.dir / self.manifest["source"]["path"]
        # Per-SUT test assets: each site owns its packs/specs/tickets so the gate for one
        # site never discovers another's cases. Defaults keep a plugin self-contained.
        tests = self.manifest.get("tests", {})
        self.packs_dir = self.dir / tests.get("packs", "packs")
        self.specs_dir = self.dir / tests.get("specs", "specs")
        self.tickets_dir = self.dir / tests.get("tickets", "tickets")
        self.ui_packs_dir = self.dir / tests.get("ui_packs", "ui-packs")  # browser-driven UI packs
        # ui.path: where the site serves its web UI, relative to the runtime base_url (e.g. "/ui").
        # None ⇒ the SUT has no UI capability (REST-only); the UI lane skips it.
        self.ui_path = self.manifest.get("ui", {}).get("path")
        self.settings = settings or Settings.load()
        self._httpd = None
        self._thread = None
        self._plugin = ...  # sentinel: not yet loaded
        self._base_url = self._resolve_base_url()
        rt = self.manifest.get("runtime", {})
        self.verify_tls = self.settings.verify_tls and rt.get("verify_tls", True)
        creds = dict(self.manifest.get("creds", {"mode": "none"}))
        if self.settings.creds_mode:  # per-run override (QAF_CREDS_MODE) of the committed manifest
            creds["mode"] = self.settings.creds_mode
        self._auth_headers = resolve_auth_headers(
            creds,
            self.settings,
            provider=getattr(self.plugin(), "resolve_creds", None) if self.plugin() else None,
        )

    # --- environment selection ---------------------------------------------
    def _resolve_base_url(self):
        """base_url precedence: --base_url/QAF_BASE_URL > --env/QAF_ENV map > runtime.base_url."""
        if self.settings.base_url:
            return self.settings.base_url
        if self.settings.env:
            envs = self.manifest.get("env", {})
            if self.settings.env not in envs:
                raise ValueError(
                    f"env {self.settings.env!r} not in manifest['env'] {list(envs)}"
                )
            url = envs[self.settings.env].get("base_url")
            if url and url.startswith("http"):
                return url
            # in-process envs (the mock's "local") have no real URL; start() fills it.
        return self.manifest.get("runtime", {}).get("base_url")

    # --- plugin hooks -------------------------------------------------------
    def plugin(self):
        """The optional ``sut/<name>/plugin.py`` module (lazy, cached), or None."""
        if self._plugin is ...:
            path = self.dir / "plugin.py"
            self._plugin = self._import_file(path, f"sut_{self.name}_plugin") if path.exists() else None
        return self._plugin

    # --- runtime access -----------------------------------------------------
    def runtime_mode(self):
        """Effective runtime mode. A selected env MAY override the manifest default, so one
        plugin can boot an ``in_process`` mock by default yet connect to a ``remote`` real
        site under ``--env live`` (e.g. restful-booker: local mock vs automationintesting.online)."""
        if self.settings.env:
            env_mode = self.manifest.get("env", {}).get(self.settings.env, {}).get("mode")
            if env_mode:
                return env_mode
        return self.manifest.get("runtime", {}).get("mode")

    def start(self, **runtime_kwargs):
        rt = self.manifest["runtime"]
        mode = self.runtime_mode()
        if mode == "in_process":
            mod = self._load_source_module(rt["app"])
            factory = getattr(mod, rt.get("factory", "make_server"))
            self._httpd = factory(**runtime_kwargs)
            self._base_url = f"http://127.0.0.1:{self._httpd.server_address[1]}"
            self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._thread.start()
        elif mode == "remote":
            if not self._base_url:
                raise ValueError("remote runtime resolved no base_url (set --env/--base_url)")
        else:
            raise ValueError(f"unknown runtime mode {mode!r}")
        return self

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()  # release the listening socket (not just serve_forever)
            self._httpd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()

    @property
    def base_url(self):
        return self._base_url

    def reachable(self) -> bool:
        """A cheap liveness probe (used by the false-green precheck)."""
        try:
            status, _ = self.get("/")
            return status < 500
        except Exception:
            return False

    def isolate(self):
        """Reset to a clean state before a case. Uses the plugin's isolate(sut) hook, else a
        manifest ``runtime.isolate`` path, else a no-op — NOT a hardcoded mock endpoint."""
        hook = getattr(self.plugin(), "isolate", None) if self.plugin() else None
        if hook is not None:
            return hook(self)
        path = self.manifest.get("runtime", {}).get("isolate")
        if path:
            self.post(path)

    def sweep_ephemerals(self, max_age_s=3600, dry_run=True):
        """Reap orphaned ephemerals left by crashed runs. Delegates to the plugin's
        ``sweep(sut, max_age, dry_run)`` (in_process has nothing to reap → [])."""
        hook = getattr(self.plugin(), "sweep", None) if self.plugin() else None
        return hook(self, max_age_s, dry_run) if hook else []

    # --- HTTP verbs ---------------------------------------------------------
    def request(self, method, path, body=None, log=False):
        url = self._base_url + path
        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.settings.user_agent,  # satisfy a real site's WAF/bot check
            **self._auth_headers,
        }
        if log:  # mask credentials at the logging boundary (policies/input-hygiene)
            print(f"    -> {method} {path} headers={mask(headers)} body={mask(body)}")
        retry_on = _RETRY_GET if method == "GET" else _RETRY_WRITE
        last_exc = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                req = urllib.request.Request(url, data=data, method=method, headers=headers)
                with urllib.request.urlopen(req, timeout=15, context=self._ssl_ctx()) as r:
                    raw = r.read()
                    return r.status, (json.loads(raw) if raw else None)
            except urllib.error.HTTPError as e:
                if e.code in retry_on and attempt < _RETRY_ATTEMPTS - 1:
                    time.sleep(_BACKOFF_BASE * (2**attempt))
                    continue
                raw = e.read()
                return e.code, (json.loads(raw) if raw else None)
            except (urllib.error.URLError, TimeoutError) as e:  # connection/timeout: retry
                last_exc = e
                if attempt < _RETRY_ATTEMPTS - 1:
                    time.sleep(_BACKOFF_BASE * (2**attempt))
                    continue
                raise
        raise last_exc  # pragma: no cover - loop always returns or raises above

    def _ssl_ctx(self):
        if not self._base_url.startswith("https"):
            return None
        if self.verify_tls:
            return None  # urllib's default verifying context
        return ssl._create_unverified_context()

    def get(self, path, log=False):
        return self.request("GET", path, log=log)

    def post(self, path, body=None, log=False):
        return self.request("POST", path, body, log=log)

    def delete(self, path, log=False):
        return self.request("DELETE", path, log=log)

    def paginate(self, first_path, items_of=lambda j: j.get("results", j), next_of=lambda j: j.get("next")):
        """Follow a list endpoint's ``next`` link to exhaustion, yielding all items.

        Single-page existence/idempotency checks false-negative as a backend's data grows
        (a recurring, product-neutral lesson); this exhausts the pages. ``items_of`` and
        ``next_of`` adapt to the plugin's list-envelope shape.
        """
        items, path = [], first_path
        while path:
            status, payload = self.get(path)
            if status >= 400 or payload is None:
                break
            items.extend(items_of(payload) or [])
            nxt = next_of(payload)
            if not nxt or nxt == path:
                break
            path = nxt if nxt.startswith("/") else "/" + nxt.split("/", 3)[-1]
        return items

    # --- source access (for design + diagnostics) ---------------------------
    def source_module(self):
        """Import the backend source as a module so design/diagnostics can read its
        declared contract (ROUTES, BUSINESS_RULES, constants)."""
        return self._load_source_module(self.manifest["runtime"]["app"])

    def source_path(self):
        return self.source_dir / self.manifest["runtime"]["app"]

    def _load_source_module(self, rel):
        return self._import_file(self.source_dir / rel, f"sut_{self.name}_{Path(rel).stem}")

    @staticmethod
    def _import_file(path, modname):
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
