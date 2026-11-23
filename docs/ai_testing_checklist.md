# Checklist: Testing AI-Enabled Analytics Features

A starting point for testing features such as a natural-language question box or AI-generated summaries on top of analytics data. This is a checklist to use when testing, not a record of tests already run.

| Area | What to check | Example test |
| --- | --- | --- |
| Functional correctness | The answer matches the data | Ask "total revenue in 2025"; compare with a SQL query |
| Groundedness | The answer uses only approved data and does not invent facts | Ask about a product that does not exist; expect "not found", not a made-up figure |
| Relevance | The answer addresses the question | Ask a specific question and check that the response stays on topic |
| Guardrails | Out-of-scope or harmful requests are refused politely | Ask for data outside the user's scope or for personal information |
| Permissions | Users see only the data they are allowed to see | Ask the same question as two roles; compare the results |
| Error handling | Bad input gives a clear message | Send empty, very long or special-character input |
| Consistency | The same question gives consistent answers | Ask the same question 5 times; compare the numbers |
| Performance | Responses arrive in an acceptable time | Time typical questions |

Record each test with the question asked, the expected outcome based on the source data, the actual response, and a pass or fail result. Log failures in `docs/defect_log.md`.
