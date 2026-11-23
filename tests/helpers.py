import sqlite3
from pathlib import Path

from src.generate_data import create_source_schema
from src.etl import run_etl


def query(db, sql, params=()):
    con = sqlite3.connect(db)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def run_small_case(folder, orders, customers=None):
    """Build a tiny source database from explicit rows, run the ETL, return the target path.
    Used for boundary / negative tests where we control every value."""
    folder = Path(folder)
    src, tgt = folder / "small_source.db", folder / "small_target.db"
    for p in (src, tgt):
        if p.exists():
            p.unlink()
    customers = customers if customers is not None else [(1, "Test User", "India", "t@example.com")]
    con = sqlite3.connect(src)
    create_source_schema(con)
    con.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)
    con.commit()
    con.close()
    run_etl(src, tgt)
    return tgt
