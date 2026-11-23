"""Generate a small, deliberately messy source database for ETL testing."""
import random
import sqlite3
from pathlib import Path

COUNTRY_VARIANTS = ["India", "india", "IN", "India ", "USA", "us", "United States", "UK", "uk", "Germany"]
STATUSES = ["Shipped", "Delivered", "Cancelled", "Pending"]


def create_source_schema(con):
    con.executescript(
        """
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS orders;
        CREATE TABLE customers (customer_id INTEGER, name TEXT, country TEXT, email TEXT);
        CREATE TABLE orders (
            order_id INTEGER, customer_id INTEGER, order_date TEXT,
            quantity INTEGER, unit_price REAL, status TEXT
        );
        """
    )


def generate_source(db_path, n_customers=50, n_orders=500, seed=42):
    """Create source.db with realistic data quality problems:
    duplicate orders, missing customer ids, negative prices, zero quantities,
    invalid dates, orphan customer ids and inconsistent country spellings."""
    rnd = random.Random(seed)
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    create_source_schema(con)

    customers = [
        (i, f"Customer {i}", rnd.choice(COUNTRY_VARIANTS), f"customer{i}@example.com")
        for i in range(1, n_customers + 1)
    ]
    con.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)

    orders = []
    for oid in range(1, n_orders + 1):
        orders.append((
            oid,
            rnd.randint(1, n_customers),
            f"2025-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}",
            rnd.randint(1, 10),
            round(rnd.uniform(5, 500), 2),
            rnd.choice(STATUSES),
        ))

    # Inject known data quality problems (counts are fixed so tests are predictable)
    for i in range(10, 25):                     # 15 duplicate order rows
        orders.append(orders[i])
    for i in range(30, 40):                     # 10 missing customer ids
        orders[i] = (orders[i][0], None) + orders[i][2:]
    for i in range(50, 58):                     # 8 negative prices
        orders[i] = orders[i][:4] + (-abs(orders[i][4]),) + orders[i][5:]
    for i in range(60, 66):                     # 6 invalid dates
        orders[i] = orders[i][:2] + ("2025-13-45",) + orders[i][3:]
    for i in range(70, 75):                     # 5 zero quantities
        orders[i] = orders[i][:3] + (0,) + orders[i][4:]
    for i in range(80, 84):                     # 4 orphan customer ids
        orders[i] = (orders[i][0], 9999) + orders[i][2:]

    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)
    con.commit()
    con.close()
    return db_path
