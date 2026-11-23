"""Automated data validation tests for the ETL pipeline.
Each test carries a test-case ID that matches test_cases/test_cases.csv.

Run:   python -m unittest -v        (or: pytest -v)
Prove the tests catch bugs:  INJECT_DEFECTS=no_dedupe python -m unittest -v
"""
import os
import tempfile
import unittest

from src.etl import ALLOWED_COUNTRIES, run_etl
from src.generate_data import generate_source
from tests.helpers import query, run_small_case


class PipelineValidation(unittest.TestCase):
    """Tests that run against the full generated dataset."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.source = os.path.join(cls._tmp.name, "source.db")
        cls.target = os.path.join(cls._tmp.name, "target.db")
        generate_source(cls.source)
        defects = tuple(d for d in os.getenv("INJECT_DEFECTS", "").split(",") if d)
        cls.stats = run_etl(cls.source, cls.target, defects=defects)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_tc01_row_count_reconciliation(self):
        """Every source order is either loaded or rejected (completeness)."""
        src_count = query(self.source, "SELECT COUNT(*) FROM orders")[0][0]
        fact = query(self.target, "SELECT COUNT(*) FROM fact_orders")[0][0]
        rej = query(self.target, "SELECT COUNT(*) FROM rejected_orders")[0][0]
        self.assertEqual(src_count, fact + rej)

    def test_tc02_no_duplicate_order_ids_in_target(self):
        dupes = query(self.target, "SELECT order_id, COUNT(*) FROM fact_orders GROUP BY order_id HAVING COUNT(*) > 1")
        self.assertEqual(dupes, [], f"Duplicate order_ids loaded: {dupes[:5]}")

    def test_tc03_no_null_customer_ids_in_target(self):
        nulls = query(self.target, "SELECT COUNT(*) FROM fact_orders WHERE customer_id IS NULL")[0][0]
        self.assertEqual(nulls, 0)

    def test_tc04_no_negative_price_or_non_positive_quantity(self):
        bad = query(self.target, "SELECT COUNT(*) FROM fact_orders WHERE unit_price < 0 OR quantity <= 0")[0][0]
        self.assertEqual(bad, 0)

    def test_tc05_order_total_equals_quantity_times_price(self):
        bad = query(self.target, "SELECT order_id FROM fact_orders WHERE ABS(order_total - quantity * unit_price) > 0.005")
        self.assertEqual(bad, [], f"Wrong order_total for orders: {[b[0] for b in bad[:5]]}")

    def test_tc06_all_loaded_dates_are_valid(self):
        bad = query(self.target, "SELECT COUNT(*) FROM fact_orders WHERE date(order_date) IS NULL")[0][0]
        self.assertEqual(bad, 0)

    def test_tc07_referential_integrity_orders_to_customers(self):
        orphans = query(
            self.target,
            "SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_customers d ON f.customer_id = d.customer_id "
            "WHERE d.customer_id IS NULL",
        )[0][0]
        self.assertEqual(orphans, 0)

    def test_tc08_country_values_are_standardized(self):
        countries = {r[0] for r in query(self.target, "SELECT DISTINCT country FROM dim_customers")}
        self.assertTrue(countries <= ALLOWED_COUNTRIES, f"Unexpected values: {countries - ALLOWED_COUNTRIES}")

    def test_tc09_every_rejected_row_has_a_reason(self):
        missing = query(self.target, "SELECT COUNT(*) FROM rejected_orders WHERE reject_reason IS NULL OR reject_reason = ''")[0][0]
        self.assertEqual(missing, 0)

    def test_tc10_customer_count_matches_source(self):
        src = query(self.source, "SELECT COUNT(*) FROM customers")[0][0]
        tgt = query(self.target, "SELECT COUNT(*) FROM dim_customers")[0][0]
        self.assertEqual(src, tgt)

    def test_tc11_rejection_reasons_match_injected_problems(self):
        """The generator injects a known number of each problem; the ETL must catch all of them."""
        rows = dict(query(self.target, "SELECT reject_reason, COUNT(*) FROM rejected_orders GROUP BY reject_reason"))
        self.assertEqual(rows.get("duplicate_order_id"), 15)
        self.assertEqual(rows.get("missing_customer_id"), 10)
        self.assertEqual(rows.get("negative_price"), 8)
        self.assertEqual(rows.get("invalid_date"), 6)
        self.assertEqual(rows.get("invalid_quantity"), 5)
        self.assertEqual(rows.get("orphan_customer_id"), 4)


class BoundaryAndNegativeCases(unittest.TestCase):
    """Small hand-built datasets so every input value is under our control."""

    def _loaded_and_rejected(self, order):
        with tempfile.TemporaryDirectory() as tmp:
            target = run_small_case(tmp, [order])
            loaded = query(target, "SELECT COUNT(*) FROM fact_orders")[0][0]
            rejected = query(target, "SELECT COUNT(*) FROM rejected_orders")[0][0]
            return loaded, rejected

    def test_tc12_quantity_boundary(self):
        for qty, expected in [(1, (1, 0)), (0, (0, 1)), (-1, (0, 1))]:
            with self.subTest(quantity=qty):
                self.assertEqual(self._loaded_and_rejected((1, 1, "2025-03-10", qty, 10.0, "Shipped")), expected)

    def test_tc13_unit_price_boundary(self):
        for price, expected in [(0.0, (1, 0)), (0.01, (1, 0)), (-0.01, (0, 1))]:
            with self.subTest(unit_price=price):
                self.assertEqual(self._loaded_and_rejected((1, 1, "2025-03-10", 1, price, "Shipped")), expected)

    def test_tc14_date_boundary_leap_year(self):
        for date, expected in [("2024-02-29", (1, 0)), ("2025-02-29", (0, 1)), ("2025-12-31", (1, 0)), ("not-a-date", (0, 1))]:
            with self.subTest(order_date=date):
                self.assertEqual(self._loaded_and_rejected((1, 1, date, 1, 10.0, "Shipped")), expected)

    def test_tc15_empty_source_loads_nothing_and_does_not_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = run_small_case(tmp, orders=[])
            self.assertEqual(query(target, "SELECT COUNT(*) FROM fact_orders")[0][0], 0)
            self.assertEqual(query(target, "SELECT COUNT(*) FROM rejected_orders")[0][0], 0)

    def test_tc16_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = run_small_case(tmp, [(1, 1, "2025-03-10", 2, 5.0, "Shipped")])
            source = os.path.join(tmp, "small_source.db")
            run_etl(source, target)  # run a second time on the same target
            self.assertEqual(query(target, "SELECT COUNT(*) FROM fact_orders")[0][0], 1)


if __name__ == "__main__":
    unittest.main()
