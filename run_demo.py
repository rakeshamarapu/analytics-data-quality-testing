"""Generate data, run the ETL, and print a source-to-target reconciliation report.

Usage:  python run_demo.py
"""
import sqlite3
from pathlib import Path

from src.etl import run_etl
from src.generate_data import generate_source

OUT = Path("output")
OUT.mkdir(exist_ok=True)
SOURCE, TARGET = OUT / "source.db", OUT / "target.db"


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def main():
    generate_source(SOURCE)
    run_etl(SOURCE, TARGET)

    con = sqlite3.connect(TARGET)
    con.execute("ATTACH DATABASE ? AS src", (str(SOURCE),))

    src_orders = scalar(con, "SELECT COUNT(*) FROM src.orders")
    loaded = scalar(con, "SELECT COUNT(*) FROM fact_orders")
    rejected = scalar(con, "SELECT COUNT(*) FROM rejected_orders")

    lines = [
        "# Source-to-Target Reconciliation Report",
        "",
        "| Check | Source | Target | Result |",
        "| --- | --- | --- | --- |",
        f"| Orders (source = loaded + rejected) | {src_orders} | {loaded + rejected} | {'PASS' if src_orders == loaded + rejected else 'FAIL'} |",
        f"| Customers | {scalar(con, 'SELECT COUNT(*) FROM src.customers')} | {scalar(con, 'SELECT COUNT(*) FROM dim_customers')} | "
        f"{'PASS' if scalar(con, 'SELECT COUNT(*) FROM src.customers') == scalar(con, 'SELECT COUNT(*) FROM dim_customers') else 'FAIL'} |",
        "",
        "## Rejected rows by reason",
        "",
        "| Reason | Rows |",
        "| --- | --- |",
    ]
    for reason, n in con.execute(
        "SELECT reject_reason, COUNT(*) FROM rejected_orders GROUP BY reject_reason ORDER BY COUNT(*) DESC"
    ):
        lines.append(f"| {reason} | {n} |")

    report = "\n".join(lines) + "\n"
    (OUT / "reconciliation_report.md").write_text(report)
    print(report)
    print(f"Report saved to {OUT / 'reconciliation_report.md'}")
    con.close()


if __name__ == "__main__":
    main()
