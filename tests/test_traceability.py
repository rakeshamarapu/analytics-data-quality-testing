"""Checks that requirements, test cases and automated tests stay linked (traceability)."""
import re
import unittest
from pathlib import Path

from src.traceability import build_matrix, load

TESTS_DIR = Path(__file__).resolve().parent


class TraceabilityChecks(unittest.TestCase):
    def test_every_requirement_has_at_least_one_test_case(self):
        requirements, matrix = build_matrix()
        uncovered = [r["Requirement ID"] for r in requirements if not matrix[r["Requirement ID"]]]
        self.assertEqual(uncovered, [], f"Requirements without test cases: {uncovered}")

    def test_every_test_case_points_to_a_known_requirement(self):
        requirements, test_cases = load()
        known = {r["Requirement ID"] for r in requirements}
        for case in test_cases:
            for req_id in [x.strip() for x in case["Requirement ID"].split(";")]:
                self.assertIn(req_id, known, f"{case['Test Case ID']} references unknown {req_id}")

    def test_every_automated_test_case_exists_in_code(self):
        _, test_cases = load()
        source = "\n".join(p.read_text(encoding="utf-8") for p in TESTS_DIR.glob("test_*.py"))
        for case in test_cases:
            match = re.match(r"Yes \((test_tc\d+)\)", case.get("Automated", ""))
            if match:
                self.assertRegex(source, rf"def {match.group(1)}_", f"{case['Test Case ID']} has no automated test")


if __name__ == "__main__":
    unittest.main()
