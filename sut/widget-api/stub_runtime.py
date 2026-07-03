"""A stand-in for the real 'widget-api' backend — used ONLY so the sourceless demo/CI has a
live runtime to hit.

Qensei does NOT read this file. sut/widget-api/manifest.json declares no ``source``, so
``SUTConnector.has_source`` is False and design/diagnostics never import it. It plays the role
of "the external system whose source we were not given": the contract lives in the ticket
(tickets/WIDGET-1.md) and the skills doc (skills/WIDGET.md), not here.

Widget contract (as the TICKET states it, not read from this code):
  * POST /widgets {name}    -> 201 {id, name, status}; a new widget starts "active"
  * GET  /widgets/{id}      -> 200 the widget, or 404
  * GET  /widgets           -> 200 the list

Pure stdlib. ``buggy=True`` makes a created widget start "inactive" instead of "active" — a
simulated regression, used to show that a sourceless diagnose can only return INDETERMINATE
(there is no readable BUSINESS_RULES oracle to prove REAL_BUG vs TEST_BUG).
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _make_handler(state, buggy):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep test output clean
            pass

        def _send(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"null") if n else {}

        def do_GET(self):
            if self.path == "/widgets":
                return self._send(200, list(state["widgets"].values()))
            if self.path.startswith("/widgets/"):
                wid = self.path.rsplit("/", 1)[-1]
                w = state["widgets"].get(wid)
                return self._send(200, w) if w else self._send(404, {"error": "not found"})
            return self._send(404, {"error": "no route"})

        def do_POST(self):
            if self.path == "/widgets":
                body = self._read_json()
                name = body.get("name")
                if not name:
                    return self._send(400, {"error": "name required"})
                state["seq"] += 1
                wid = str(state["seq"])
                # A created widget starts "active" per the ticket. `buggy` starts it "inactive"
                # (a simulated regression) so a sourceless diagnose has a failing case to classify.
                widget = {"id": wid, "name": name, "status": "inactive" if buggy else "active"}
                state["widgets"][wid] = widget
                return self._send(201, widget)
            return self._send(404, {"error": "no route"})

    return Handler


def make_server(buggy: bool = False) -> ThreadingHTTPServer:
    """Bind on an ephemeral port (127.0.0.1:0). The caller reads the real port."""
    state = {"widgets": {}, "seq": 0}
    return ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state, buggy))


if __name__ == "__main__":
    srv = make_server()
    print(f"widget-api stub on http://127.0.0.1:{srv.server_address[1]}")
    srv.serve_forever()
