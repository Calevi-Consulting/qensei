"""SUTConnector — the generic "backend access" abstraction.

This is the seam that makes the framework domain-agnostic. A System Under Test
plugin (a directory under sut/<name>/) declares, in manifest.json:

  * runtime : how to reach the RUNNING system
              - {"mode": "in_process", "app": "app.py", "factory": "make_server"}
                (the mock: the framework boots the backend in-process)
              - {"mode": "remote", "base_url": "https://..."}   (a real backend)
  * source  : where the backend SOURCE lives (read by design + diagnostics)
  * env     : environments / base URLs
  * creds   : credential resolution (stubbed for the mock; Vault/env for real)
  * knowledge: skills + learnings dirs (domain manual-QA context)

Both things the framework needs — calling the live API AND reading the backend
source — go through this one object. Test-design and diagnostics both depend on
source access; the regression engine depends on runtime access.
"""
from __future__ import annotations

import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path


class SUTConnector:
    def __init__(self, sut_dir):
        self.dir = Path(sut_dir).resolve()
        self.manifest = json.loads((self.dir / "manifest.json").read_text())
        self.name = self.manifest["name"]
        self.source_dir = self.dir / self.manifest["source"]["path"]
        self._httpd = None
        self._thread = None
        self._base_url = self.manifest.get("runtime", {}).get("base_url")

    # --- runtime access -----------------------------------------------------
    def start(self, **runtime_kwargs):
        rt = self.manifest["runtime"]
        if rt["mode"] == "in_process":
            mod = self._load_source_module(rt["app"])
            factory = getattr(mod, rt.get("factory", "make_server"))
            self._httpd = factory(**runtime_kwargs)
            self._base_url = f"http://127.0.0.1:{self._httpd.server_address[1]}"
            self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._thread.start()
        elif rt["mode"] == "remote":
            self._base_url = rt["base_url"]
        else:
            raise ValueError(f"unknown runtime mode {rt['mode']!r}")
        return self

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()

    @property
    def base_url(self):
        return self._base_url

    # --- HTTP verbs ---------------------------------------------------------
    def request(self, method, path, body=None):
        url = self._base_url + path
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        # A real plugin would inject an auth token here from manifest["creds"].
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, (json.loads(raw) if raw else None)

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body=None):
        return self.request("POST", path, body)

    # --- source access (for design + diagnostics) ---------------------------
    def source_module(self):
        """Import the backend source as a module so design/diagnostics can read
        its declared contract (ROUTES, BUSINESS_RULES, constants). For a real
        remote backend this would parse a checked-out clone instead."""
        return self._load_source_module(self.manifest["runtime"]["app"])

    def source_path(self):
        return self.source_dir / self.manifest["runtime"]["app"]

    def _load_source_module(self, rel):
        path = self.source_dir / rel
        spec = importlib.util.spec_from_file_location(
            f"sut_{self.name}_{Path(rel).stem}", path
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
