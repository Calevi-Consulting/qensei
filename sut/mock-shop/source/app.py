"""mock-shop — the System Under Test for the qa-framework demo.

Pure stdlib (http.server), zero dependencies. This single file is BOTH:

  * the RUNTIME the regression engine tests against (start a server), and
  * the SOURCE the design + diagnostics layers read to learn the intended contract.

The DECLARED CONTRACT lives in ROUTES + BUSINESS_RULES + the DISCOUNT_* constants
below. Because that contract is readable, the diagnostics layer can compare "what
the backend is supposed to do" against "what it actually returned" and classify a
failure as REAL_BUG vs TEST_BUG.

A tiny "shop": products, a cart, and a checkout that applies a bulk discount.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# --- declared business contract (read by engine/design.py + engine/diagnostics.py) ---
DISCOUNT_RATE = 0.10  # 10% off the subtotal
DISCOUNT_MIN_QTY = 3  # ... once the cart holds at least 3 items total

# Durable store: accounts persist ACROSS server boots (a file), unlike the ephemeral cart.
# This is what makes the existing_data find-or-create / durability demo real — a baseline
# created on the first run is re-read (not recreated) on later runs — the way a
# qaf-keep durable survives across runs and DB migrations.
ACCOUNTS_FILE = Path(os.environ.get("QAF_MOCK_STATE", Path(__file__).parent / ".accounts.json"))

PRODUCTS = {
    1: {"id": 1, "name": "Widget", "price": 10.0},
    2: {"id": 2, "name": "Gadget", "price": 25.0},
    3: {"id": 3, "name": "Gizmo", "price": 4.0},
}

ROUTES = [
    ("GET", "/products", "list products"),
    ("GET", "/products/{id}", "get one product (404 if missing)"),
    ("POST", "/cart", "add {product_id, qty}; returns {items, total}"),
    ("GET", "/cart", "current cart"),
    ("POST", "/cart/clear", "empty the cart"),
    ("POST", "/checkout", "create an order; applies the bulk-discount rule"),
    ("GET", "/accounts/{name}", "get a durable account by name (404 if missing)"),
    ("POST", "/accounts", "find-or-create a durable account {name, plan}; persists across boots"),
]


def _load_accounts():
    try:
        return json.loads(ACCOUNTS_FILE.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _save_accounts(accounts):
    ACCOUNTS_FILE.write_text(json.dumps(accounts))

BUSINESS_RULES = [
    {
        "id": "bulk-discount",
        "endpoint": "/checkout",
        "description": "If total quantity >= DISCOUNT_MIN_QTY, apply DISCOUNT_RATE off the subtotal.",
        "rate": DISCOUNT_RATE,
        "min_qty": DISCOUNT_MIN_QTY,
    },
]


def _make_handler(state, buggy):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep the demo output clean
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

        def _cart_view(self):
            items = state["cart"]
            total = sum(PRODUCTS[i["product_id"]]["price"] * i["qty"] for i in items)
            return {"items": items, "total": round(total, 2)}

        def do_GET(self):
            if self.path == "/products":
                return self._send(200, list(PRODUCTS.values()))
            if self.path.startswith("/products/"):
                pid = self.path.rsplit("/", 1)[-1]
                p = PRODUCTS.get(int(pid)) if pid.isdigit() else None
                return self._send(200, p) if p else self._send(404, {"error": "not found"})
            if self.path == "/cart":
                return self._send(200, self._cart_view())
            if self.path.startswith("/accounts/"):
                from urllib.parse import unquote

                name = unquote(self.path.split("/accounts/", 1)[1])
                acct = _load_accounts().get(name)
                return self._send(200, acct) if acct else self._send(404, {"error": "no account"})
            return self._send(404, {"error": "no route"})

        def do_POST(self):
            if self.path == "/cart":
                body = self._read_json()
                pid = int(body.get("product_id"))
                qty = int(body.get("qty", 1))
                if pid not in PRODUCTS:
                    return self._send(400, {"error": "unknown product"})
                state["cart"].append({"product_id": pid, "qty": qty})
                return self._send(200, self._cart_view())
            if self.path == "/cart/clear":
                state["cart"] = []
                return self._send(200, {"items": [], "total": 0.0})
            if self.path == "/accounts":  # find-or-create a DURABLE account (persists across boots)
                body = self._read_json()
                name = body.get("name")
                if not name:
                    return self._send(400, {"error": "name required"})
                accounts = _load_accounts()
                if name in accounts:
                    return self._send(200, {**accounts[name], "created": False})
                acct = {"name": name, "plan": body.get("plan", "free")}
                accounts[name] = acct
                _save_accounts(accounts)
                return self._send(201, {**acct, "created": True})
            if self.path == "/checkout":
                view = self._cart_view()
                subtotal = view["total"]
                total_qty = sum(i["qty"] for i in state["cart"])
                discount = 0.0
                if total_qty >= DISCOUNT_MIN_QTY and not buggy:
                    discount = round(subtotal * DISCOUNT_RATE, 2)
                # When `buggy` is set, the discount branch is skipped — this simulates a
                # platform REGRESSION. The declared contract (BUSINESS_RULES) still says the
                # discount applies, which is exactly what lets diagnostics call it a REAL_BUG.
                order = {
                    "items": view["items"],
                    "subtotal": subtotal,
                    "discount": discount,
                    "total": round(subtotal - discount, 2),
                }
                state["cart"] = []
                return self._send(201, order)
            return self._send(404, {"error": "no route"})

    return Handler


def make_server(buggy: bool = False) -> ThreadingHTTPServer:
    """Bind on an ephemeral port (127.0.0.1:0). The connector reads the real port."""
    state = {"cart": []}
    return ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state, buggy))


if __name__ == "__main__":
    srv = make_server(buggy=False)
    print(f"mock-shop on http://127.0.0.1:{srv.server_address[1]}")
    srv.serve_forever()
