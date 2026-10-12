"""Tests for the endpoint monitor, using only a local HTTP server.

Using a local server makes the tests repeatable and prevents them from
depending on an internet connection or on a third-party website.
"""

import csv
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from monitor import check_endpoint, load_endpoints, save_report


class Handler(BaseHTTPRequestHandler):
    """Return predictable responses for the monitor tests."""

    def do_GET(self):
        # The /slow route lets us verify that a request timeout is handled.
        if self.path == "/slow":
            import time
            time.sleep(0.15)

        # Return an error only for /unavailable; all other routes are healthy.
        status = 503 if self.path == "/unavailable" else 200
        body = b"ok"
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def log_message(self, *_args):
        pass


class MonitorTests(unittest.TestCase):
    """Check configuration, endpoint status handling, and CSV reporting."""

    @classmethod
    def setUpClass(cls):
        # Port 0 asks the operating system for a free port, avoiding conflicts.
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        # Stop the shared test server after all tests have finished.
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_config_loads_defaults_and_endpoint_overrides(self):
        # The first endpoint relies on global defaults; the second overrides them.
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "endpoints.json"
            config.write_text(json.dumps({
                "timeout_seconds": 3,
                "endpoints": [
                    {"name": "one", "url": "http://localhost/"},
                    {"name": "two", "url": "https://localhost/", "expected_status": 204, "timeout_seconds": 1},
                ],
            }), encoding="utf-8")
            old_folder = os.getcwd()
            try:
                os.chdir(directory)
                endpoints = load_endpoints()
            finally:
                os.chdir(old_folder)
        self.assertEqual((endpoints[0]["expected_status"], endpoints[0]["timeout_seconds"]), (200, 3))
        self.assertEqual((endpoints[1]["expected_status"], endpoints[1]["timeout_seconds"]), (204, 1))

    def test_empty_endpoint_list_is_rejected(self):
        # A configuration without endpoints cannot perform any monitoring.
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "endpoints.json"
            config.write_text(json.dumps({"endpoints": []}), encoding="utf-8")
            old_folder = os.getcwd()
            try:
                os.chdir(directory)
                with self.assertRaisesRegex(ValueError, "at least one endpoint"):
                    load_endpoints()
            finally:
                os.chdir(old_folder)

    def test_success_records_status_and_elapsed_time(self):
        # A matching expected status produces an UP result and no error.
        result = check_endpoint({"name": "healthy", "url": self.base + "/", "expected_status": 200, "timeout_seconds": 1})
        self.assertEqual((result["result"], result["status"]), ("UP", 200))
        self.assertGreaterEqual(result["response_time_ms"], 0)
        self.assertEqual(result["error"], "")

    def test_unexpected_http_status_is_down(self):
        # A real HTTP response is still DOWN when it differs from the expected code.
        result = check_endpoint({"name": "unavailable", "url": self.base + "/unavailable", "expected_status": 200, "timeout_seconds": 1})
        self.assertEqual((result["result"], result["status"]), ("DOWN", 503))
        self.assertIn("Expected 200", result["error"])

    def test_expected_http_error_status_is_up(self):
        # Any status can be considered healthy when it is explicitly expected.
        result = check_endpoint({"name": "unavailable", "url": self.base + "/unavailable", "expected_status": 503, "timeout_seconds": 1})
        self.assertEqual((result["result"], result["status"], result["error"]), ("UP", 503, ""))

    def test_timeout_is_captured_without_raising(self):
        # A slow endpoint should create a DOWN result instead of crashing the monitor.
        result = check_endpoint({"name": "slow", "url": self.base + "/slow", "expected_status": 200, "timeout_seconds": 0.02})
        self.assertEqual(result["result"], "DOWN")
        self.assertEqual(result["status"], "")
        self.assertTrue(result["error"])

    def test_connection_error_is_captured_without_raising(self):
        # Reserve then release an ephemeral port to obtain a local closed port.
        # This simulates a service that is not running.
        probe = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = probe.server_port
        probe.server_close()
        result = check_endpoint({"name": "closed", "url": f"http://127.0.0.1:{port}/", "expected_status": 200, "timeout_seconds": 0.5})
        self.assertEqual(result["result"], "DOWN")
        self.assertEqual(result["status"], "")
        self.assertTrue(result["error"])

    def test_csv_report_contains_results(self):
        # Verify that a successful check is written to the CSV report.
        result = check_endpoint({"name": "healthy", "url": self.base + "/", "expected_status": 200, "timeout_seconds": 1})
        with tempfile.TemporaryDirectory() as directory:
            old_folder = os.getcwd()
            try:
                os.chdir(directory)
                save_report([result])
            finally:
                os.chdir(old_folder)
            report = Path(directory) / "monitoring_report.csv"
            with report.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["result"], "UP")
        self.assertEqual(rows[0]["status"], "200")

    def test_empty_csv_report_still_contains_headers(self):
        # Even with no results, the CSV must retain its column headings.
        with tempfile.TemporaryDirectory() as directory:
            old_folder = os.getcwd()
            try:
                os.chdir(directory)
                save_report([])
            finally:
                os.chdir(old_folder)
            report = Path(directory) / "monitoring_report.csv"
            with report.open(encoding="utf-8", newline="") as source:
                rows = list(csv.reader(source))
        self.assertEqual(rows, [["time", "name", "url", "status", "response_time_ms", "result", "error"]])


if __name__ == "__main__":
    unittest.main()
