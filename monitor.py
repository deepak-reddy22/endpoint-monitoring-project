"""Check configured websites and APIs and save a monitoring report.

The program reads endpoint definitions from ``endpoints.json``, performs one
check for each endpoint, and writes the results to a CSV file and a log file.
"""

import csv
import json
import logging
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def load_endpoints():
    """Read endpoint settings from endpoints.json."""
    # The configuration file contains global defaults and the endpoint list.
    with open("endpoints.json", encoding="utf-8") as file:
        config = json.load(file)

    # Use five seconds when no global timeout has been configured.
    default_timeout = config.get("timeout_seconds", 5)
    endpoints = config.get("endpoints", [])

    # Running without endpoints would produce a misleading empty report.
    if not endpoints:
        raise ValueError("Add at least one endpoint to endpoints.json")

    # Add defaults to each endpoint so check_endpoint can use the same fields
    # even when an endpoint omits optional settings.
    for endpoint in endpoints:
        endpoint.setdefault("expected_status", 200)
        endpoint.setdefault("timeout_seconds", default_timeout)

    return endpoints


def check_endpoint(endpoint):
    """Check one endpoint and return its result as a dictionary."""
    # Start timing before making the request so response time includes the
    # complete network operation.
    start_time = time.time()
    status_code = ""
    error = ""

    try:
        # urlopen supports HTTP and HTTPS URLs without extra dependencies.
        with urlopen(endpoint["url"], timeout=endpoint["timeout_seconds"]) as response:
            status_code = response.status
            # Read the response body so the request completes cleanly.
            response.read()
    except HTTPError as problem:
        # An HTTP error such as 404 still has a status code worth reporting.
        status_code = problem.code
    except (TimeoutError, URLError, OSError) as problem:
        # Connection failures and timeouts are recorded instead of stopping
        # the remaining endpoint checks.
        error = str(getattr(problem, "reason", problem))

    # Convert seconds to milliseconds for a more useful report value.
    response_time = round((time.time() - start_time) * 1000, 2)

    # An endpoint is healthy only when its status matches the configured
    # expectation and no network error was recorded.
    is_up = status_code == endpoint["expected_status"] and not error

    if is_up:
        # Log successful checks for later review in monitoring.log.
        result = "UP"
        logging.info("%s is UP (%s ms)", endpoint["name"], response_time)
    else:
        # A failed request or unexpected status is reported as DOWN.
        result = "DOWN"
        if not error:
            # HTTP responses such as 404 or 503 reach this branch with no
            # network exception, so create a helpful explanation manually.
            error = f"Expected {endpoint['expected_status']}, got {status_code}"
        logging.error("%s is DOWN: %s", endpoint["name"], error)

    # Return a consistent record used by both the console output and CSV file.
    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": endpoint["name"],
        "url": endpoint["url"],
        "status": status_code,
        "response_time_ms": response_time,
        "result": result,
        "error": error,
    }


def save_report(results):
    """Save all check results to monitoring_report.csv."""
    # Keep a fixed column order so the report is easy to read and process.
    columns = ["time", "name", "url", "status", "response_time_ms", "result", "error"]
    with open("monitoring_report.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        # Always write the header, even when results is empty.
        writer.writeheader()
        writer.writerows(results)


def main():
    # Write informational messages and failures to monitoring.log.
    logging.basicConfig(
        filename="monitoring.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        # Load and validate the endpoint configuration before checking URLs.
        endpoints = load_endpoints()
    except (OSError, ValueError, json.JSONDecodeError) as problem:
        # Configuration errors are shown to the user and recorded in the log.
        print(f"Could not read endpoints.json: {problem}")
        logging.error("Could not read endpoints.json: %s", problem)
        return

    # Check every configured endpoint and keep all results for the CSV report.
    results = []
    for endpoint in endpoints:
        result = check_endpoint(endpoint)
        results.append(result)
        # Show a short status line immediately in the terminal.
        print(f"{result['name']}: {result['result']} - HTTP {result['status']} - {result['response_time_ms']} ms")

    # Save the complete run after all endpoints have been checked.
    save_report(results)
    print("\nSaved report to monitoring_report.csv")
    print("Saved log to monitoring.log")


if __name__ == "__main__":
    # Only run the monitor automatically when this file is executed directly.
    main()
