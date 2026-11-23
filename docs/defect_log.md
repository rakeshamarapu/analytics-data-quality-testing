# Defect Log

Defects found by running the test suite against the ETL with simulated bugs
(`INJECT_DEFECTS=<name> python -m unittest -v`). Results below are from actual runs.

| ID | Title | Severity | Failing tests | Steps to reproduce | Expected | Actual | Business impact | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEF-001 | Duplicate orders loaded into fact_orders | High | TC-02, TC-11 | Run `INJECT_DEFECTS=no_dedupe python -m unittest -v` | Each order_id loaded once; 15 duplicates rejected | 15 order_ids (11 to 25) loaded twice; no `duplicate_order_id` rejections | Revenue and order counts overstated in reports | Fixed (dedupe rule in etl.py) |
| DEF-002 | Negative unit prices accepted | High | TC-04, TC-11 | Run `INJECT_DEFECTS=keep_negative python -m unittest -v` | Rows with unit_price < 0 rejected | 8 rows with negative price loaded | Negative revenue distorts totals and averages | Fixed (price rule in etl.py) |
| DEF-003 | order_total truncated to whole number | Medium | TC-05 | Run `INJECT_DEFECTS=wrong_total python -m unittest -v` | order_total = quantity x unit_price (2 decimals) | order_total cut to an integer, so most rows differ from quantity x unit_price | Revenue understated; dashboard totals do not match source | Fixed (rounding in etl.py) |

## Template for new defects

| Field | Value |
| --- | --- |
| ID | DEF-00X |
| Title | Short, specific summary |
| Severity / Priority | High / Medium / Low |
| Environment | Python version, database, dataset |
| Steps to reproduce | Numbered steps |
| Expected result | What should happen |
| Actual result | What happened, with evidence (query output, screenshot) |
| Business impact | Who or what is affected |
| Status | New / In progress / Fixed / Retested / Closed |
