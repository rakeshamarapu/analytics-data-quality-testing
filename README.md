# Analytics Data Quality Testing

A small, end-to-end quality engineering project for analytics data. It contains an ETL pipeline, an automated validation test suite, SQL source-to-target reconciliation checks, a manual test case sheet and a defect log.

## What it demonstrates

- **Source-to-target validation:** row counts, completeness, duplicates, nulls, calculations, referential integrity
- **ETL testing:** positive, negative, boundary and failure scenarios (empty source, re-runs, leap-year dates)
- **Test design:** 18 documented test cases (16 automated, 2 manual) with IDs that match the code
- **Defect reporting:** reproducible defects with expected vs actual results and business impact
- **SQL and Python:** reconciliation queries and `unittest` automation (also runs under `pytest`)

## Project structure

```
src/generate_data.py          creates a messy source database (duplicates, nulls, bad dates, etc.)
src/etl.py                    cleans and loads data into dim_customers, fact_orders, rejected_orders
tests/test_data_validation.py 16 automated tests (TC-01 to TC-16)
sql/reconciliation_checks.sql manual reconciliation queries
test_cases/test_cases.csv     full test case sheet (TC-01 to TC-18)
docs/defect_log.md            defect log and template
run_demo.py                   runs the pipeline and writes a reconciliation report
```

## How to run

Requires Python 3.9+ only. No packages to install.

```bash
python run_demo.py            # generate data, run ETL, print reconciliation report
python -m unittest -v         # run all automated tests (or: pip install pytest && pytest -v)
```

## Prove the tests work

Simulate known ETL bugs and watch the tests fail:

```bash
# Mac / Linux
INJECT_DEFECTS=no_dedupe python -m unittest -v
INJECT_DEFECTS=keep_negative python -m unittest -v
INJECT_DEFECTS=wrong_total python -m unittest -v

# Windows (PowerShell)
$env:INJECT_DEFECTS="no_dedupe"; python -m unittest -v
```

| Injected defect | Tests that fail |
| --- | --- |
| `no_dedupe` | TC-02, TC-11 |
| `keep_negative` | TC-04, TC-11 |
| `wrong_total` | TC-05 |

## Sample reconciliation result

Running `python run_demo.py` gives 515 source orders = 467 loaded + 48 rejected. Every rejected row carries a reason: duplicate_order_id 15, missing_customer_id 10, negative_price 8, invalid_date 6, invalid_quantity 5, orphan_customer_id 4.

## Ideas to extend

- Add a Power BI or Tableau dashboard on `fact_orders` and write test cases for its filters, totals and drill-downs
- Add API tests with Postman (or Python `requests`) and keep the collection in the repo
- Add a GitHub Actions workflow that runs the tests on every push
