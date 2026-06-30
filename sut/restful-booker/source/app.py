"""restful-booker — the System Under Test for the qa-framework's SECOND site.

A zero-dependency stdlib (http.server) mock of mwinteringham's **restful-booker-platform**
(live at https://automationintesting.online/, source at
https://github.com/mwinteringham/restful-booker-platform). Like mock-shop it is BOTH:

  * the RUNTIME the regression engine tests against (start a server), and
  * the SOURCE the design + diagnostics layers read to learn the intended contract.

It reproduces the real platform's surface faithfully — the auth/room/booking endpoints and
the real **"overlapping dates are rejected with 409"** rule — so the *same* engine that runs
mock-shop runs this site unchanged (`--sut sut/restful-booker`). On top of the real surface
it adds ONE illustrative, declared business rule — a **long-stay discount** — to exercise the
diagnosable REAL_BUG/TEST_BUG seam exactly as mock-shop's bulk discount does. Both facts (the
faithful 409 rule and the illustrative discount) are documented in BUSINESS_RULES below.

Differences from the live API, kept deliberately small and documented:
  * auth is NOT enforced on writes, so the offline gate needs no credentials. The real site
    enforces a session ``token`` on writes — that path is demonstrated by ``plugin.py``'s
    ``resolve_creds`` against the ``live`` env (see manifest.json + skills/BOOKER.md). The real
    API is served under ``/api`` (the bare host is the UI); the ``live`` env carries that prefix.
  * a booking response carries a computed ``totalprice`` (roomPrice x nights, minus the
    long-stay discount). The live booking model has no price field; the frontend computes it —
    so the discount/price packs are mock-scoped, while the 409 availability rule is live-faithful.
"""
from __future__ import annotations

import datetime
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# --- declared business contract (read by engine/design.py + engine/diagnostics.py) ---
LONGSTAY_RATE = 0.15       # 15% off the room subtotal ...
LONGSTAY_MIN_NIGHTS = 7    # ... once a stay is at least 7 nights long
ADMIN_USER = "admin"       # the platform's documented default credentials
ADMIN_PASS = "password"

# Durable store: ROOMS persist ACROSS server boots (a file), like mock-shop's accounts and
# unlike the ephemeral bookings. This is what makes the existing_data / durability demo real:
# a find-or-created "keep" room survives a reboot and is re-read, not recreated.
ROOMS_FILE = Path(os.environ.get("QAF_BOOKER_STATE", Path(__file__).parent / ".rooms.json"))

DEFAULT_ROOMS = {
    1: {"roomid": 1, "roomName": "101", "type": "Single", "accessible": True,
        "image": "", "description": "Cosy single room.", "features": ["WiFi", "TV"], "roomPrice": 100},
    2: {"roomid": 2, "roomName": "201", "type": "Double", "accessible": False,
        "image": "", "description": "Spacious double room.", "features": ["WiFi", "TV", "Safe"], "roomPrice": 150},
}

ROUTES = [
    ("GET", "/ui", "the booking web UI (HTML form) — the Playwright UI sample drives this"),
    ("POST", "/auth/login", "log in {username,password}; returns a token (403 on bad creds)"),
    ("POST", "/auth/validate", "validate {token}"),
    ("POST", "/auth/logout", "log out {token}"),
    ("GET", "/room/", "list rooms {rooms:[...]}"),
    ("GET", "/room/{id}", "get one room (404 if missing)"),
    ("POST", "/room/", "create a room; returns it with an assigned roomid"),
    ("DELETE", "/room/{id}", "delete a room"),
    ("GET", "/booking/", "list bookings (optionally ?roomid=)"),
    ("GET", "/booking/{id}", "get one booking (404 if missing)"),
    ("POST", "/booking/", "create a booking; applies long-stay discount; 409 on overlap/bad dates"),
    ("DELETE", "/booking/{id}", "delete a booking"),
    ("GET", "/booking/summary", "?roomid= -> the booked date ranges for a room"),
    ("POST", "/message/", "submit a contact message"),
]

BUSINESS_RULES = [
    {
        "id": "longstay-discount",
        "endpoint": "/booking/",
        "description": "If a stay is >= LONGSTAY_MIN_NIGHTS nights, apply LONGSTAY_RATE off the "
                       "room subtotal (roomPrice x nights). Illustrative rule added by this mock "
                       "to exercise the diagnosable REAL_BUG/TEST_BUG seam.",
        "rate": LONGSTAY_RATE,
        "min_nights": LONGSTAY_MIN_NIGHTS,
    },
    {
        "id": "no-double-booking",
        "endpoint": "/booking/",
        "description": "A booking whose dates overlap an existing booking on the same room is "
                       "rejected with HTTP 409. checkin >= checkout is likewise rejected. This is "
                       "the real restful-booker-platform behaviour, reproduced faithfully.",
    },
]


# A minimal, self-contained booking WEB UI served at GET /ui. It is the deterministic, offline
# stand-in for the real site's front-end (just as the JSON API above stands in for the real API):
# the Playwright UI sample (sut/restful-booker/ui-packs/) drives THIS page. The form loads rooms
# from GET /room/ and submits to POST /booking/, then shows a #confirmation (or #error). Stable
# element ids (#firstname, #room, #book-btn, #confirmation, ...) are the UI contract the case pins.
BOOKING_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Restful Booker (mock) — Book a room</title></head>
<body>
  <h1>Book a room</h1>
  <form id="booking-form">
    <label>First name <input id="firstname" name="firstname" required></label>
    <label>Last name <input id="lastname" name="lastname" required></label>
    <label>Room <select id="room" name="roomid"></select></label>
    <label>Check-in <input id="checkin" name="checkin" type="date" required></label>
    <label>Check-out <input id="checkout" name="checkout" type="date" required></label>
    <button id="book-btn" type="submit">Book</button>
  </form>
  <p id="confirmation" hidden></p>
  <p id="error" hidden></p>
  <script>
    async function loadRooms() {
      const res = await fetch('/room/');
      const data = await res.json();
      const sel = document.getElementById('room');
      (data.rooms || []).forEach(function (r) {
        const o = document.createElement('option');
        o.value = r.roomid;
        o.textContent = 'Room ' + r.roomName + ' (' + r.roomPrice + '/night)';
        sel.appendChild(o);
      });
    }
    document.getElementById('booking-form').addEventListener('submit', async function (e) {
      e.preventDefault();
      const body = {
        roomid: parseInt(document.getElementById('room').value, 10),
        firstname: document.getElementById('firstname').value,
        lastname: document.getElementById('lastname').value,
        depositpaid: true,
        bookingdates: {
          checkin: document.getElementById('checkin').value,
          checkout: document.getElementById('checkout').value
        }
      };
      const res = await fetch('/booking/', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
      });
      const conf = document.getElementById('confirmation');
      const err = document.getElementById('error');
      if (res.status === 201) {
        const data = await res.json();
        conf.textContent = 'Booking confirmed - id ' + data.bookingid + ', total ' + data.booking.totalprice;
        conf.hidden = false; err.hidden = true;
      } else {
        const data = await res.json().catch(function () { return {}; });
        err.textContent = 'Booking failed: ' + ((data && data.error) || res.status);
        err.hidden = false; conf.hidden = true;
      }
    });
    loadRooms();
  </script>
</body>
</html>
"""


def _load_rooms():
    try:
        raw = json.loads(ROOMS_FILE.read_text())
        return {int(k): v for k, v in raw.items()}
    except (FileNotFoundError, ValueError):
        return dict(DEFAULT_ROOMS)


def _save_rooms(rooms):
    ROOMS_FILE.write_text(json.dumps({str(k): v for k, v in rooms.items()}))


def _as_int(value):
    """Coerce to int, or None if not integer-like — the caller maps None to a clean 400
    (so a malformed request gets an HTTP verdict, never an unhandled crash / dropped socket)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value):
    """ISO date string -> datetime.date, or None on bad input (caller maps to a 4xx)."""
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _overlaps(a_in, a_out, b_in, b_out) -> bool:
    """Half-open [checkin, checkout) ranges overlap iff each starts before the other ends.
    Compares datetime.date objects (not raw strings), so non-zero-padded ISO can't skew it."""
    return a_in < b_out and b_in < a_out


def _make_handler(state, buggy):
    rooms = _load_rooms()
    if not ROOMS_FILE.exists():
        _save_rooms(rooms)  # seed defaults on first boot so the durable file exists

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep the demo output clean
            pass

        # --- helpers --------------------------------------------------------
        def _send(self, code, payload):
            body = json.dumps(payload).encode() if payload is not None else b""
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html):
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"null") if n else {}

        def _path_id(self, prefix):
            tail = self.path.split(prefix, 1)[1].split("?", 1)[0].strip("/")
            return int(tail) if tail.isdigit() else None

        def _next_booking_id(self):
            state["seq"] += 1
            return state["seq"]

        # --- GET ------------------------------------------------------------
        def do_GET(self):
            route = urlparse(self.path)
            path, query = route.path, parse_qs(route.query)

            if path in ("/", ""):
                return self._send(200, {"service": "restful-booker-platform (mock)"})
            if path == "/ui":  # the booking web UI the Playwright sample drives
                return self._send_html(BOOKING_UI_HTML)

            if path == "/room/":
                return self._send(200, {"rooms": list(rooms.values())})
            if path.startswith("/room/"):
                rid = self._path_id("/room/")
                room = rooms.get(rid) if rid is not None else None
                return self._send(200, room) if room else self._send(404, {"error": "room not found"})

            if path == "/booking/":
                items = list(state["bookings"].values())
                if "roomid" in query:
                    rid = _as_int(query["roomid"][0])
                    if rid is None:
                        return self._send(400, {"error": "roomid must be an integer"})
                    items = [b for b in items if b["roomid"] == rid]
                return self._send(200, {"bookings": items})
            if path == "/booking/summary":
                rid = _as_int(query.get("roomid", [None])[0])
                if rid is None:
                    return self._send(400, {"error": "roomid query param required (integer)"})
                dates = [{"bookingdates": b["bookingdates"]} for b in state["bookings"].values() if b["roomid"] == rid]
                return self._send(200, {"bookings": dates})
            if path.startswith("/booking/"):
                bid = self._path_id("/booking/")
                bk = state["bookings"].get(bid) if bid is not None else None
                return self._send(200, bk) if bk else self._send(404, {"error": "booking not found"})

            if path == "/message/":
                return self._send(200, {"messages": list(state["messages"].values())})

            return self._send(404, {"error": "no route"})

        # --- POST -----------------------------------------------------------
        def do_POST(self):
            path = urlparse(self.path).path

            if path == "/auth/login":
                body = self._read_json()
                if body.get("username") == ADMIN_USER and body.get("password") == ADMIN_PASS:
                    return self._send(200, {"token": "qaf-mock-session-token"})
                return self._send(403, {"error": "invalid credentials"})
            if path == "/auth/validate":
                ok = self._read_json().get("token") == "qaf-mock-session-token"
                return self._send(200 if ok else 403, {"valid": ok})
            if path == "/auth/logout":
                return self._send(200, {})

            if path == "/room/":  # create a (durable) room
                body = self._read_json()
                name = body.get("roomName")
                if not name:
                    return self._send(400, {"error": "roomName required"})
                # find-or-create by roomName so a durable "keep" room is not duplicated on re-runs
                for room in rooms.values():
                    if room["roomName"] == name:
                        return self._send(200, {**room, "created": False})
                price = _as_int(body.get("roomPrice", 100))
                if price is None:
                    return self._send(400, {"error": "roomPrice must be an integer"})
                rid = (max(rooms) + 1) if rooms else 1
                room = {
                    "roomid": rid, "roomName": name, "type": body.get("type", "Single"),
                    "accessible": bool(body.get("accessible", False)), "image": body.get("image", ""),
                    "description": body.get("description", ""), "features": body.get("features", []),
                    "roomPrice": price,
                }
                rooms[rid] = room
                _save_rooms(rooms)
                return self._send(201, {**room, "created": True})

            if path == "/booking/reset":  # TEST SEAM (mock-only): clear ephemeral bookings
                state["bookings"].clear()
                return self._send(200, {"bookings": []})

            if path == "/booking/":
                return self._create_booking(self._read_json())

            if path == "/message/":
                body = self._read_json()
                for f in ("name", "email", "subject", "description"):
                    if not body.get(f):
                        return self._send(400, {"error": f"{f} required"})
                mid = self._next_message_id()
                fields = ("name", "email", "phone", "subject", "description")
                msg = {"messageid": mid, **{k: body.get(k, "") for k in fields}}
                state["messages"][mid] = msg
                return self._send(201, msg)

            return self._send(404, {"error": "no route"})

        def _next_message_id(self):
            state["mseq"] += 1
            return state["mseq"]

        def _create_booking(self, body):
            roomid = _as_int(body.get("roomid"))
            if roomid is None:
                return self._send(400, {"error": "roomid must be an integer"})
            dates = body.get("bookingdates")
            dates = dates if isinstance(dates, dict) else {}  # tolerate a non-object bookingdates
            checkin, checkout = dates.get("checkin"), dates.get("checkout")
            for f, v in (("firstname", body.get("firstname")), ("lastname", body.get("lastname")),
                         ("checkin", checkin), ("checkout", checkout)):
                if not v:
                    return self._send(400, {"error": f"{f} required"})
            room = rooms.get(roomid)
            if room is None:
                return self._send(400, {"error": "unknown room"})
            ci, co = _parse_date(checkin), _parse_date(checkout)
            if ci is None or co is None:
                return self._send(400, {"error": "bad date format (expected YYYY-MM-DD)"})
            nights = (co - ci).days
            if nights <= 0:  # checkin >= checkout — real API rejects with 409
                return self._send(409, {"error": "checkout must be after checkin"})
            # real rule: reject a stay overlapping an existing booking on the same room
            for b in state["bookings"].values():
                if b["roomid"] == roomid:
                    bd = b["bookingdates"]
                    if _overlaps(ci, co, _parse_date(bd["checkin"]), _parse_date(bd["checkout"])):
                        return self._send(409, {"error": "room not available for those dates"})

            subtotal = room["roomPrice"] * nights
            discount = 0
            if nights >= LONGSTAY_MIN_NIGHTS and not buggy:
                discount = round(subtotal * LONGSTAY_RATE, 2)
            # When `buggy` is set, the long-stay discount branch is skipped — this simulates a
            # platform REGRESSION. The declared contract (BUSINESS_RULES) still says the discount
            # applies, which is exactly what lets diagnostics call it a REAL_BUG.
            bid = self._next_booking_id()
            booking = {
                "bookingid": bid, "roomid": roomid,
                "firstname": body["firstname"], "lastname": body["lastname"],
                "depositpaid": bool(body.get("depositpaid", False)),
                "bookingdates": {"checkin": checkin, "checkout": checkout},
                "email": body.get("email", ""), "phone": body.get("phone", ""),
                "subtotal": subtotal, "discount": discount,
                "totalprice": round(subtotal - discount, 2),
            }
            state["bookings"][bid] = booking
            return self._send(201, {"bookingid": bid, "booking": booking})

        # --- DELETE ---------------------------------------------------------
        def do_DELETE(self):
            path = urlparse(self.path).path
            if path.startswith("/booking/"):
                bid = self._path_id("/booking/")
                state["bookings"].pop(bid, None)
                return self._send(200, {})
            if path.startswith("/room/"):
                rid = self._path_id("/room/")
                if rid in rooms:
                    del rooms[rid]
                    _save_rooms(rooms)
                return self._send(200, {})
            return self._send(404, {"error": "no route"})

    return Handler


def make_server(buggy: bool = False) -> ThreadingHTTPServer:
    """Bind on an ephemeral port (127.0.0.1:0). The connector reads the real port."""
    state = {"bookings": {}, "messages": {}, "seq": 0, "mseq": 0}
    return ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state, buggy))


if __name__ == "__main__":
    srv = make_server(buggy=False)
    print(f"restful-booker mock on http://127.0.0.1:{srv.server_address[1]}")
    srv.serve_forever()
