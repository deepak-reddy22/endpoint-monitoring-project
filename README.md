# Simple Website Monitor

This program checks a list of websites or APIs. It prints whether each one is up, saves results to a CSV file, and keeps a log.

## Run it

1. Make a copy of `endpoints.example.json` and name it `endpoints.json`.
2. Add your endpoint names and URLs to `endpoints.json`.
3. Open a terminal in this folder and run:

   ```text
   python3 monitor.py
   ```

The program creates `monitoring_report.csv` and `monitoring.log` in the same folder.

## Settings

Each endpoint needs a name and URL. `expected_status` is the status code you expect (usually 200). `timeout_seconds` is how long to wait for a response. Both settings can be set for all endpoints or changed for one endpoint.

## Tests

Run the tests with `python3 -m unittest -v`. They use a small local web server and do not need public websites.

See [TEST_CASES.md](./TEST_CASES.md) for the test-case matrix and expected outcomes.

## View the report in a browser

Generate a report first:

```text
python3 monitor.py
```

Start the dashboard:

```text
python3 dashboard.py
```

Open http://localhost:8000 in a browser. The dashboard displays the latest `monitoring_report.csv` and also provides:

- `/health` for a service health check
- `/api/report` for the latest report as JSON
