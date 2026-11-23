"""Automated API tests (status codes, schema, validation, data accuracy, performance).
Test-case IDs match test_cases/test_cases.csv.
"""
import json
import os
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from src.api_server import start_server
from src.etl import ALLOWED_COUNTRIES, run_etl
from src.generate_data import generate_source
from tests.helpers import query

ORDER_FIELDS = {"order_id", "customer_id", "order_date", "quantity", "unit_price", "order_total", "status"}


def call(base, path, method="GET"):
    """Return (status, headers, parsed_json) for any status code, including 4xx."""
    request = urllib.request.Request(base + path, method=method, data=b"{}" if method != "GET" else None)
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, resp.headers, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, err.headers, json.loads(err.read())


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        source = os.path.join(cls._tmp.name, "source.db")
        cls.db = os.path.join(cls._tmp.name, "target.db")
        generate_source(source)
        run_etl(source, cls.db)
        cls.server = start_server(cls.db)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._tmp.cleanup()

    def test_tc19_health_endpoint(self):
        status, headers, body = call(self.base, "/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(body, {"status": "ok"})

    def test_tc20_list_orders_default_page_and_schema(self):
        status, _, body = call(self.base, "/orders")
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 10)
        self.assertEqual(body["limit"], 10)
        for order in body["orders"]:
            self.assertEqual(set(order), ORDER_FIELDS)

    def test_tc21_limit_boundary_values(self):
        for limit, expected in [("1", 200), ("100", 200), ("0", 400), ("101", 400), ("-5", 400), ("abc", 400)]:
            with self.subTest(limit=limit):
                self.assertEqual(call(self.base, f"/orders?limit={limit}")[0], expected)

    def test_tc22_offset_pagination_has_no_overlap(self):
        _, _, page1 = call(self.base, "/orders?limit=5&offset=0")
        _, _, page2 = call(self.base, "/orders?limit=5&offset=5")
        ids1 = {o["order_id"] for o in page1["orders"]}
        ids2 = {o["order_id"] for o in page2["orders"]}
        self.assertEqual(len(ids1), 5)
        self.assertEqual(len(ids2), 5)
        self.assertTrue(ids1.isdisjoint(ids2))
        self.assertEqual(call(self.base, "/orders?offset=-1")[0], 400)

    def test_tc23_order_by_id_matches_database_and_total_is_correct(self):
        rows = query(self.db, "SELECT order_id FROM fact_orders ORDER BY order_id LIMIT 20")
        for (order_id,) in rows:
            with self.subTest(order_id=order_id):
                status, _, order = call(self.base, f"/orders/{order_id}")
                self.assertEqual(status, 200)
                db_row = query(self.db, "SELECT customer_id, quantity, unit_price, order_total FROM fact_orders WHERE order_id=?", (order_id,))[0]
                self.assertEqual((order["customer_id"], order["quantity"], order["unit_price"], order["order_total"]), db_row)
                self.assertAlmostEqual(order["order_total"], order["quantity"] * order["unit_price"], places=2)

    def test_tc24_order_not_found_and_invalid_id(self):
        for path, expected in [("/orders/99999", 404), ("/orders/-1", 404), ("/orders/abc", 400), ("/orders/1.5", 400)]:
            with self.subTest(path=path):
                status, _, body = call(self.base, path)
                self.assertEqual(status, expected)
                self.assertIn("error", body)

    def test_tc25_rejected_orders_are_not_exposed(self):
        rejected_id = query(self.db, "SELECT order_id FROM rejected_orders WHERE reject_reason='missing_customer_id' LIMIT 1")[0][0]
        self.assertEqual(call(self.base, f"/orders/{rejected_id}")[0], 404)

    def test_tc26_customer_endpoint_returns_standardized_country(self):
        status, _, customer = call(self.base, "/customers/1")
        self.assertEqual(status, 200)
        self.assertIn(customer["country"], ALLOWED_COUNTRIES)
        self.assertEqual(call(self.base, "/customers/9999")[0], 404)
        self.assertEqual(call(self.base, "/customers/abc")[0], 400)

    def test_tc27_summary_matches_database(self):
        status, _, summary = call(self.base, "/summary")
        self.assertEqual(status, 200)
        self.assertEqual(summary["total_orders"], query(self.db, "SELECT COUNT(*) FROM fact_orders")[0][0])
        self.assertEqual(summary["rejected_orders"], query(self.db, "SELECT COUNT(*) FROM rejected_orders")[0][0])
        self.assertAlmostEqual(summary["total_revenue"], query(self.db, "SELECT SUM(quantity*unit_price) FROM fact_orders")[0][0], places=1)

    def test_tc28_unsupported_methods_return_405(self):
        for method in ["POST", "PUT", "DELETE", "PATCH"]:
            with self.subTest(method=method):
                status, headers, _ = call(self.base, "/orders", method=method)
                self.assertEqual(status, 405)
                self.assertEqual(headers["Allow"], "GET")

    def test_tc29_unknown_route_returns_json_404(self):
        status, headers, body = call(self.base, "/does-not-exist")
        self.assertEqual(status, 404)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertIn("error", body)

    def test_tc30_response_time_under_one_second(self):
        for path in ["/health", "/orders?limit=100", "/summary"]:
            with self.subTest(path=path):
                start = time.perf_counter()
                call(self.base, path)
                self.assertLess(time.perf_counter() - start, 1.0)


if __name__ == "__main__":
    unittest.main()
