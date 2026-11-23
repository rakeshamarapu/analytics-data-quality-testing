# API Testing

The project includes a small read-only REST API (`src/api_server.py`) over the cleaned `target.db`, with two ways to test it.

## 1. Automated Python tests (no setup)

```bash
python -m unittest tests.test_api -v
```

12 tests (TC-19 to TC-30) start the API on a random free port and check status codes, JSON schema, input validation (boundary values for `limit` and `offset`), pagination, data accuracy against the database, 404/405 handling, and response time.

## 2. Postman collection

1. Generate the data and start the API:
   ```bash
   python run_demo.py
   python -m src.api_server --db output/target.db --port 8000
   ```
2. In Postman: **Import** > `api_testing/orders_api.postman_collection.json`.
3. Run the collection (Runner). The `base_url` variable defaults to `http://localhost:8000`.

Each request carries Postman test scripts (status code, response fields, error messages, response time). The collection assumes the default generated dataset.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | /health | Service status |
| GET | /orders?limit=&offset=&customer_id= | Paged order list (limit 1-100, default 10) |
| GET | /orders/{id} | One loaded order |
| GET | /customers/{id} | One customer |
| GET | /summary | Loaded orders, revenue, rejected orders |
