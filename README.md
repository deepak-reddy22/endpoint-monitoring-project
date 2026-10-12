# Endpoint Monitoring Project

Endpoint Monitoring Project is a lightweight Python application that checks websites, APIs, and local services to confirm that they are responding correctly.

It is designed to be easy to understand and run. The monitor reads endpoint settings from a JSON file, sends an HTTP request to each endpoint, compares the response with the expected status code, and records the result as `UP` or `DOWN`.

The project also includes a local web dashboard that displays the latest monitoring report in a browser.

## What the project does

For every configured endpoint, the monitor records:

- Endpoint name and URL
- HTTP status code
- Response time in milliseconds
- `UP` or `DOWN` result
- Error details when a request fails

The project currently checks public websites and local dashboard routes such as `/health` and `/api/report`.

## How it works

```text
endpoints.json
       |
       v
   monitor.py  --->  monitoring_report.csv
       |                    |
       v                    v
 monitoring.log       dashboard.py
                            |
                            v
                    Browser: localhost:8000
```

`monitor.py` performs a single monitoring run. `dashboard.py` starts a local website that reads and displays the latest CSV report.

## Project files

| File | Purpose |
| --- | --- |
| `monitor.py` | Checks all configured endpoints and creates the report and log. |
| `dashboard.py` | Serves the report as a browser dashboard. |
| `endpoints.json` | Contains the endpoints to monitor. |
| `endpoints.example.json` | Example configuration template. |
| `monitoring_report.csv` | Latest monitoring results. |
| `monitoring.log` | History of successful and failed checks. |
| `test_monitor.py` | Automated tests for the monitor. |
| `TEST_CASES.md` | Test scenario descriptions and expected outcomes. |

## Configure endpoints

Add endpoints to `endpoints.json` using this format:

```json
{
  "name": "Example API",
  "url": "https://api.example.com/health",
  "expected_status": 200,
  "timeout_seconds": 5
}
```

`expected_status` defaults to `200`. Each endpoint can have its own timeout, or the top-level `timeout_seconds` value can be used as the default.

## Run the local dashboard

Open a terminal in the project directory and start the dashboard:

```bash
python3 dashboard.py
```

Keep that terminal open, then visit:

```text
http://127.0.0.1:8000
```

The dashboard provides these routes:

- `/` — Report dashboard
- `/health` — Service health response
- `/api/report` — Latest report in JSON format

## Generate or update the report

In a second terminal, run:

```bash
python3 monitor.py
```

Refresh the browser dashboard after running the monitor. The local endpoints will show `UP` only while the dashboard server is running.

## Run the tests

Run the automated tests with:

```bash
python3 -m unittest -v
```

The tests use a temporary local HTTP server. They cover configuration defaults, successful checks, unexpected status codes, timeouts, connection errors, and CSV report creation. They do not depend on public websites.

See [TEST_CASES.md](./TEST_CASES.md) for the complete test-case matrix.

## Simple explanation

This project is a small uptime checker. It asks each configured website, “Are you available, and did you return the status code I expected?” It saves the answers in a report and shows them on a simple dashboard so the results are easy to understand.
