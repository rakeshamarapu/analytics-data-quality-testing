"""A small ETL pipeline: source.db -> cleaned target.db (star-schema style).

`defects` lets the test suite simulate known bugs so you can show that the
tests actually catch them (see README, "Prove the tests work").
"""
import sqlite3
from datetime import datetime

COUNTRY_MAP = {
    "india": "India", "in": "India",
    "usa": "USA", "us": "USA", "united states": "USA",
    "uk": "UK", "united kingdom": "UK",
}
ALLOWED_COUNTRIES = {"India", "USA", "UK", "Germany", "Unknown"}


def standardize_country(value):
    if value is None or not value.strip():
        return "Unknown"
    key = value.strip().lower()
    return COUNTRY_MAP.get(key, value.strip().title())


def is_valid_date(text):
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def create_target_schema(con):
    con.executescript(
        """
        DROP TABLE IF EXISTS dim_customers;
        DROP TABLE IF EXISTS fact_orders;
        DROP TABLE IF EXISTS rejected_orders;
        CREATE TABLE dim_customers (customer_id INTEGER PRIMARY KEY, name TEXT, country TEXT, email TEXT);
        CREATE TABLE fact_orders (
            order_id INTEGER, customer_id INTEGER, order_date TEXT,
            quantity INTEGER, unit_price REAL, order_total REAL, status TEXT
        );
        CREATE TABLE rejected_orders (
            order_id INTEGER, customer_id INTEGER, order_date TEXT,
            quantity INTEGER, unit_price REAL, status TEXT, reject_reason TEXT
        );
        """
    )


def run_etl(source_db, target_db, defects=()):
    defects = set(defects)
    src = sqlite3.connect(source_db)
    tgt = sqlite3.connect(target_db)
    create_target_schema(tgt)

    customers = src.execute("SELECT customer_id, name, country, email FROM customers").fetchall()
    tgt.executemany(
        "INSERT INTO dim_customers VALUES (?,?,?,?)",
        [(cid, name, standardize_country(country), email) for cid, name, country, email in customers],
    )
    known_customers = {c[0] for c in customers}

    seen_orders = set()
    loaded, rejected = 0, 0
    for oid, cid, odate, qty, price, status in src.execute(
        "SELECT order_id, customer_id, order_date, quantity, unit_price, status FROM orders ORDER BY rowid"
    ):
        reason = None
        if cid is None:
            reason = "missing_customer_id"
        elif cid not in known_customers:
            reason = "orphan_customer_id"
        elif qty is None or qty <= 0:
            reason = "invalid_quantity"
        elif price is None or (price < 0 and "keep_negative" not in defects):
            reason = "negative_price"
        elif not is_valid_date(odate):
            reason = "invalid_date"
        elif oid in seen_orders and "no_dedupe" not in defects:
            reason = "duplicate_order_id"

        if reason:
            tgt.execute("INSERT INTO rejected_orders VALUES (?,?,?,?,?,?,?)",
                        (oid, cid, odate, qty, price, status, reason))
            rejected += 1
            continue

        seen_orders.add(oid)
        total = int(qty * price) if "wrong_total" in defects else round(qty * price, 2)
        tgt.execute("INSERT INTO fact_orders VALUES (?,?,?,?,?,?,?)",
                    (oid, cid, odate, qty, price, total, status))
        loaded += 1

    tgt.commit()
    src.close()
    tgt.close()
    return {"loaded": loaded, "rejected": rejected}
