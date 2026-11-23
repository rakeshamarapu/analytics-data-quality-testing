# Dashboard Testing

`imdb_dashboard_test_cases.csv` holds 14 manual test cases for the IMDB Movies Power BI dashboard (data accuracy, slicers and filters, drill-down, null handling, usability, export).

## How to use

1. Open the dashboard and the source data side by side (SQL, Excel or the raw CSV).
2. Run each test case. Record the result in **Status** (`Pass` / `Fail`) and write what you saw in **Actual Result**.
3. For every failure, add a row to `docs/defect_log.md` with steps, expected vs actual result and business impact.
4. Re-run `python -m src.traceability` to refresh the traceability matrix.

All cases start as **Not executed**. Only claim dashboard testing on your resume after you have run them and recorded real results.
