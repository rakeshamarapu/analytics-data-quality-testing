"""A small read-only REST API over the cleaned target database (standard library only).

Run:  python -m src.api_server --db output/target.db --port 8000
Endpoints:
  GET /health
  GET /orders?limit=10&offset=0&customer_id=5
  GET /orders/{order_id}
  GET /customers/{customer_id}
  GET /summary
"""
import argparse
import json
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_LIMIT = 10
MAX_LIMIT = 100
INT_PATTERN = re.compile(r"-?\d+")


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep test output quiet
            pass

        def _send(self, status, payload, extra_headers=None):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def _rows(self, sql, params=()):
            con = sqlite3.connect(db_path)
            con.row_factory = sqlite3.Row
            try:
                return [dict(r) for r in con.execute(sql, params).fetchall()]
            finally:
                con.close()

        def _int_param(self, params, name, default, minimum, maximum=None):
            raw = params.get(name, [None])[0]
            if raw is None:
                return default, None
            if not INT_PATTERN.fullmatch(raw):
                return None, f"{name} must be an integer"
            value = int(raw)
            if value < minimum or (maximum is not None and value > maximum):
                bound = f"between {minimum} and {maximum}" if maximum is not None else f">= {minimum}"
                return None, f"{name} must be {bound}"
            return value, None

        def do_GET(self):
            parsed = urlparse(self.path)
            path, params = parsed.path.rstrip("/") or "/", parse_qs(parsed.query)

            if path == "/health":
                return self._send(200, {"status": "ok"})

            if path == "/orders":
                limit, err = self._int_param(params, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT)
                if err:
                    return self._send(400, {"error": err})
                offset, err = self._int_param(params, "offset", 0, 0)
                if err:
                    return self._send(400, {"error": err})
                customer_id, err = self._int_param(params, "customer_id", None, 1)
                if err:
                    return self._send(400, {"error": err})
                sql, args = "SELECT * FROM fact_orders", []
                if customer_id is not None:
                    sql += " WHERE customer_id = ?"
                    args.append(customer_id)
                sql += " ORDER BY order_id LIMIT ? OFFSET ?"
                rows = self._rows(sql, args + [limit, offset])
                return self._send(200, {"count": len(rows), "limit": limit, "offset": offset, "orders": rows})

            match = re.fullmatch(r"/orders/([^/]+)", path)
            if match:
                if not INT_PATTERN.fullmatch(match.group(1)):
                    return self._send(400, {"error": "order_id must be an integer"})
                rows = self._rows("SELECT * FROM fact_orders WHERE order_id = ?", (int(match.group(1)),))
                return self._send(200, rows[0]) if rows else self._send(404, {"error": "order not found"})

            match = re.fullmatch(r"/customers/([^/]+)", path)
            if match:
                if not INT_PATTERN.fullmatch(match.group(1)):
                    return self._send(400, {"error": "customer_id must be an integer"})
                rows = self._rows("SELECT * FROM dim_customers WHERE customer_id = ?", (int(match.group(1)),))
                return self._send(200, rows[0]) if rows else self._send(404, {"error": "customer not found"})

            if path == "/summary":
                row = self._rows(
                    "SELECT (SELECT COUNT(*) FROM fact_orders) AS total_orders, "
                    "ROUND((SELECT COALESCE(SUM(order_total), 0) FROM fact_orders), 2) AS total_revenue, "
                    "(SELECT COUNT(*) FROM rejected_orders) AS rejected_orders"
                )[0]
                return self._send(200, row)

            return self._send(404, {"error": "route not found"})

        def _method_not_allowed(self):
            # Read and discard any request body first; replying while the body is unread
            # can abort the connection on some platforms (seen on Windows).
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            self._send(405, {"error": "method not allowed"}, {"Allow": "GET"})

        do_POST = do_PUT = do_PATCH = do_DELETE = _method_not_allowed

    return Handler


def start_server(db_path, host="127.0.0.1", port=0):
    """Start the API in a background thread (port=0 picks a free port). Returns the server."""
    server = ThreadingHTTPServer((host, port), make_handler(db_path))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="output/target.db")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.db))
    print(f"Serving on http://127.0.0.1:{args.port}  (Ctrl+C to stop)")
    server.serve_forever()