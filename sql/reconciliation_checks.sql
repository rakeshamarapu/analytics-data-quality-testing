-- Source-to-target reconciliation checks (SQLite).
-- Usage (after running `python run_demo.py`):
--   sqlite3 output/target.db
--   .read sql/reconciliation_checks.sql

ATTACH DATABASE 'output/source.db' AS src;

-- 1. Row count: source orders must equal loaded + rejected (expected difference = 0)
SELECT (SELECT COUNT(*) FROM src.orders)
     - (SELECT COUNT(*) FROM fact_orders)
     - (SELECT COUNT(*) FROM rejected_orders) AS row_count_difference;

-- 2. Duplicate order ids in target (expected: no rows)
SELECT order_id, COUNT(*) AS copies
FROM fact_orders GROUP BY order_id HAVING COUNT(*) > 1;

-- 3. Null checks on mandatory columns (expected: 0)
SELECT COUNT(*) AS null_mandatory_values
FROM fact_orders
WHERE customer_id IS NULL OR order_date IS NULL OR quantity IS NULL OR unit_price IS NULL;

-- 4. Calculation check: order_total = quantity * unit_price (expected: no rows)
SELECT order_id, quantity, unit_price, order_total
FROM fact_orders
WHERE ABS(order_total - quantity * unit_price) > 0.005;

-- 5. Orders in source missing from both target tables (expected: no rows)
SELECT DISTINCT s.order_id
FROM src.orders s
WHERE s.order_id NOT IN (SELECT order_id FROM fact_orders)
  AND s.order_id NOT IN (SELECT order_id FROM rejected_orders);

-- 6. Referential integrity: loaded orders without a customer (expected: 0)
SELECT COUNT(*) AS orphan_orders
FROM fact_orders f LEFT JOIN dim_customers d ON f.customer_id = d.customer_id
WHERE d.customer_id IS NULL;

-- 7. Revenue reconciliation: loaded revenue must equal revenue recalculated from the loaded rows (difference = 0)
SELECT ROUND((SELECT SUM(order_total) FROM fact_orders) - (SELECT SUM(quantity * unit_price) FROM fact_orders), 2) AS revenue_difference;

-- 8. Country standardization (expected: only India, USA, UK, Germany, Unknown)
SELECT country, COUNT(*) AS customers FROM dim_customers GROUP BY country;
