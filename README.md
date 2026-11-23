# Analytics Data Quality Testing

An end-to-end quality engineering project for analytics data: an ETL pipeline, a read-only API, automated tests, SQL reconciliation checks, requirement traceability, manual dashboard test cases and a defect log.

## What it demonstrates

- **Source-to-target validation:** row counts, completeness, duplicates, nulls, calculations, referential integrity
- **ETL testing:** positive, negative and boundary scenarios, including an empty source, re-runs and leap-year dates
- **API testing:** status codes, schema, input validation, pagination, data accuracy against the database, performance (Python tests and a Postman collection)
- **Requirements and traceability:** 14 requirements written as user stories with acceptance criteria, mapped to test cases, with an automated check that nothing is uncovered
- **Test design:** 30 documented test cases (28 automated, 2 manual) plus 14 manual dashboard test cases
- **Regression:** 31 automated tests, run on every push by GitHub Actions
- **Defect reporting:** a log with reproduction steps, expected vs actual results and business impact

## Project structure

```
src/generate_data.py            creates a messy source database
src/etl.py                      cleans and loads data into dim_customers, fact_orders, rejected_orders
src/api_server.py               read-only REST API over the target database
src/traceability.py             builds the requirement traceability matrix
tests/test_data_validation.py   ETL tests (TC-01 to TC-16)
tests/test_api.py               API tests (TC-19 to TC-30)
tests/test_traceability.py      checks requirements, test cases and code stay linked
sql/reconciliation_checks.sql   manual reconciliation queries
test_cases/test_cases.csv       all test cases with requirement IDs
docs/requirements.csv           user stories and acceptance criteria
docs/traceability_matrix.md     generated requirement to test case matrix
docs/defect_log.md              defect log and template
docs/ai_testing_checklist.md    checklist for testing AI-enabled analytics features
api_testing/                    Postman collection and API test guide
dashboard_testing/              manual test cases for the Power BI dashboard
.github/workflows/tests.yml     runs the regression suite on every push
run_demo.py                     runs the pipeline and writes a reconciliation report
```

## How to run

Requires Python 3.9+ only. No packages to install.

```bash
python run_demo.py              # generate data, run ETL, print reconciliation report
python -m unittest -v           # run all 31 automated tests (or: pip install pytest && pytest -v)
python -m src.traceability      # refresh docs/traceability_matrix.md
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

## Test the API

```bash
python run_demo.py
python -m src.api_server --db output/target.db --port 8000
```

Then import `api_testing/orders_api.postman_collection.json` into Postman. See `api_testing/README.md`.
