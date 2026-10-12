"""Small web dashboard for the endpoint monitor report.

The dashboard reads the CSV created by ``monitor.py`` and presents the latest
results in a browser. It deliberately uses only Python's standard library so
it can be run without installing extra packages.
"""

import csv
import json
import os
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


# Keep the report path relative to this file, not to the directory from which
# the command is run. This makes the dashboard work from any current folder.
PROJECT_DIR = Path(__file__).resolve().parent
REPORT_FILE = PROJECT_DIR / "monitoring_report.csv"

# Hosting platforms commonly provide the port through the PORT environment
# variable. The defaults make local development work at localhost:8000.
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))


def load_report():
    """Load the latest report rows, returning an empty list if unavailable."""
    # The dashboard should still open when monitor.py has not been run yet.
    if not REPORT_FILE.exists():
        return []

    # DictReader turns each CSV row into a dictionary using the header names.
    with REPORT_FILE.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def page_html(rows):
    """Render the latest report as a simple, readable dashboard."""
    # Count the results for the summary cards at the top of the page.
    up_count = sum(row.get("result") == "UP" for row in rows)
    down_count = sum(row.get("result") == "DOWN" for row in rows)
    checked_at = rows[0].get("time", "-") if rows else "No report generated yet"

    # Convert each CSV row into one safe HTML table row. escape() prevents
    # endpoint names, URLs, or error messages from being interpreted as HTML.
    table_rows = "".join(
        "<tr>"
        f"<td>{escape(row.get('name', ''))}</td>"
        f"<td><code>{escape(row.get('url', ''))}</code></td>"
        f"<td>{escape(row.get('status') or '-')}</td>"
        f"<td>{escape(row.get('response_time_ms') or '-')} ms</td>"
        f"<td class='{row.get('result', '').lower()}'>{escape(row.get('result', '-'))}</td>"
        f"<td>{escape(row.get('error') or '-')}</td>"
        "</tr>"
        for row in rows
    )

    # Give the user a useful message when no report exists yet.
    if not table_rows:
        table_rows = "<tr><td colspan='6'>No monitoring report found. Run monitor.py first.</td></tr>"

    # The page is intentionally self-contained: HTML and CSS are returned
    # directly so there are no templates or front-end dependencies to install.
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Endpoint Monitor Dashboard</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f7fb; color: #172033; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px; }}
    h1 {{ margin-bottom: 4px; }}
    .muted {{ color: #667085; }}
    .cards {{ display: flex; gap: 16px; margin: 24px 0; flex-wrap: wrap; }}
    .card {{ background: white; border-radius: 12px; padding: 18px 24px; min-width: 130px; box-shadow: 0 2px 8px #17203312; }}
    .number {{ display: block; font-size: 28px; font-weight: 700; }}
    /* Green means the endpoint returned its expected status. */
    .up {{ color: #087443; font-weight: 700; }}
    /* Red means the endpoint could not be checked or returned an unexpected status. */
    .down {{ color: #b42318; font-weight: 700; }}
    .table-wrap {{ overflow-x: auto; background: white; border-radius: 12px; box-shadow: 0 2px 8px #17203312; }}
    table {{ border-collapse: collapse; width: 100%; min-width: 760px; }}
    th, td {{ text-align: left; padding: 14px 16px; border-bottom: 1px solid #eaecf0; }}
    th {{ background: #eef4ff; }}
    code {{ font-size: 0.9em; }}
  </style>
</head>
<body>
  <main>
    <h1>Endpoint Monitor Dashboard</h1>
    <p class="muted">A simple view of the latest availability checks.</p>
    <div class="cards">
      <div class="card"><span class="muted">Total endpoints</span><span class="number">{len(rows)}</span></div>
      <div class="card"><span class="muted">Up</span><span class="number up">{up_count}</span></div>
      <div class="card"><span class="muted">Down</span><span class="number down">{down_count}</span></div>
    </div>
    <p class="muted">Last checked: {escape(checked_at)}</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Name</th><th>URL</th><th>HTTP status</th><th>Response time</th><th>Result</th><th>Error</th></tr></thead>
      <tbody>{table_rows}</tbody>
    </table></div>
  </main>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    """Serve the dashboard, JSON report, and health endpoint."""

    def send_body(self, body, content_type="text/html; charset=utf-8", status=200):
        """Send a text response with the headers required by the browser."""
        # Encode once so Content-Length reports bytes rather than characters.
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        """Route browser GET requests to the appropriate response."""
        path = urlparse(self.path).path
        if path == "/":
            # Main page: reload the CSV on every request so new reports appear.
            self.send_body(page_html(load_report()))
        elif path == "/api/report":
            # Machine-readable version for future integrations or charts.
            self.send_body(json.dumps(load_report()), "application/json; charset=utf-8")
        elif path == "/health":
            # Lightweight service check used by hosting platforms and monitors.
            self.send_body('{"status":"ok"}', "application/json; charset=utf-8")
        else:
            # Unknown paths receive the standard HTTP 404 response.
            self.send_error(404, "Not found")

    def log_message(self, format, *args):
        """Print requests to the terminal instead of using default web logs."""
        print(format % args)


if __name__ == "__main__":
    # Start a threaded server so multiple browsers can view the dashboard.
    print(f"Dashboard running at http://127.0.0.1:{PORT}")
    ThreadingHTTPServer((HOST, PORT), DashboardHandler).serve_forever()
