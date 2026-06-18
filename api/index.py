"""
Vercel Serverless Function — SmartAttend API Gateway.

Forwards all /api/v1/* requests to the FastAPI backend.

NOTE: Vercel free tier has limitations:
- No WebSockets (live session feed unavailable)
- No long-running processes (Celery worker/beat won't run here)
- 10s function timeout
- 250MB deploy size

For full functionality, run the backend + Celery + Redis on a dedicated host
(Render, Railway, Fly.io, or your own VPS) and point BACKEND_URL to it.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

BACKEND_URL = os.environ.get("BACKEND_URL", "")


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler — proxies API requests to the backend."""

    def do_request(self):
        if not BACKEND_URL:
            self.send_error_json(
                502,
                "BACKEND_URL not configured. "
                "Set it in Vercel environment variables.",
            )
            return

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Build target URL
        path = self.path  # e.g. /api/v1/auth/login
        url = f"{BACKEND_URL}{path}"

        # Forward headers
        headers = {}
        skip = {"content-length", "host", "transfer-encoding", "connection"}
        for key, value in self.headers.items():
            if key.lower() not in skip:
                headers[key] = value

        req = urllib.request.Request(url, data=body, headers=headers, method=self.command)

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.send_response(resp.status)
                resp_headers = resp.getheaders()
                for key, value in resp_headers:
                    if key.lower() not in skip:
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_body = e.read() if e.fp else b'{"detail":"upstream error"}'
            self.wfile.write(error_body)
        except Exception as e:
            self.send_error_json(502, str(e))

    def do_GET(self):
        self.do_request()

    def do_POST(self):
        self.do_request()

    def do_PUT(self):
        self.do_request()

    def do_PATCH(self):
        self.do_request()

    def do_DELETE(self):
        self.do_request()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.end_headers()

    def send_error_json(self, code, message):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"detail": message}).encode())
