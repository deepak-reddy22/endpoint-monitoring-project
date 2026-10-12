# Endpoint Monitor Test Cases

The automated tests in [`test_monitor.py`](./test_monitor.py) use a local HTTP server, so they do not make public-network requests.

| ID | Area | Scenario | Expected result |
| --- | --- | --- | --- |
| TC-01 | Configuration | Load an endpoint without optional settings | `expected_status` defaults to `200` and `timeout_seconds` defaults to the global timeout |
| TC-02 | Configuration | Load an endpoint with per-endpoint overrides | Per-endpoint values are preserved |
| TC-03 | Configuration | Load a configuration with no endpoints | `ValueError` is raised with a message asking for at least one endpoint |
| TC-04 | Availability | Endpoint returns HTTP 200 and 200 is expected | Result is `UP`, status is `200`, and the response time is non-negative |
| TC-05 | Availability | Endpoint returns HTTP 503 while 200 is expected | Result is `DOWN`, status is `503`, and the error explains the expected status |
| TC-06 | Availability | Endpoint returns HTTP 503 and 503 is expected | Result is `UP`, status is `503`, and no error is recorded |
| TC-07 | Availability | Endpoint exceeds its timeout | Result is `DOWN` without propagating the timeout exception |
| TC-08 | Availability | Endpoint connection is refused | Result is `DOWN` without propagating the connection exception |
| TC-09 | Reporting | Save one endpoint result | CSV contains one data row with the result and status |
| TC-10 | Reporting | Save an empty result collection | CSV is created with the expected header row |

## Run the tests

From the project directory, run:

```text
python3 -m unittest -v
```

If the system `python3` is unavailable, use the interpreter configured for the project environment instead.
