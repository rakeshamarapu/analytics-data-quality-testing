"""Build a requirement-to-test traceability matrix and flag uncovered requirements.

Usage:  python -m src.traceability     (writes docs/traceability_matrix.md)
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "docs" / "requirements.csv"
TEST_CASE_FILES = [ROOT / "test_cases" / "test_cases.csv", ROOT / "dashboard_testing" / "imdb_dashboard_test_cases.csv"]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load():
    requirements = read_csv(REQUIREMENTS)
    test_cases = [row for path in TEST_CASE_FILES for row in read_csv(path)]
    return requirements, test_cases


def build_matrix():
    requirements, test_cases = load()
    matrix = {r["Requirement ID"]: [] for r in requirements}
    for case in test_cases:
        for req_id in [x.strip() for x in case["Requirement ID"].split(";") if x.strip()]:
            matrix.setdefault(req_id, []).append(case["Test Case ID"])
    return requirements, matrix


def write_matrix():
    requirements, matrix = build_matrix()
    lines = ["# Requirement Traceability Matrix", "",
             "| Requirement | Title | Priority | Test cases | Count |", "| --- | --- | --- | --- | --- |"]
    for r in requirements:
        ids = matrix[r["Requirement ID"]]
        lines.append(f"| {r['Requirement ID']} | {r['Title']} | {r['Priority']} | {', '.join(ids) or 'NONE'} | {len(ids)} |")
    uncovered = [r["Requirement ID"] for r in requirements if not matrix[r["Requirement ID"]]]
    lines += ["", f"Uncovered requirements: {', '.join(uncovered) if uncovered else 'none'}", ""]
    out = ROOT / "docs" / "traceability_matrix.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out, uncovered


if __name__ == "__main__":
    path, missing = write_matrix()
    print(f"Written {path}")
    print("Uncovered:", missing or "none")
