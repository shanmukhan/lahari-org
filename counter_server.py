#!/usr/bin/env python3
"""Tiny stdlib-only HTTP service backing the visitor counter on lahari.org.

Exposes GET /api/visits: increments the persistent counter and returns
{"count": N} as JSON. Everything else gets 404. Runs as a systemd service on
127.0.0.1, reverse-proxied by Apache at /api/ (see rpi-setup's
configure-lahari.sh + apache-templates/lahari.org.conf.tmpl) — deliberately
dependency-free since a framework would add nothing for one endpoint.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from counter_store import CounterStore

DEFAULT_COUNTER_PATH = "/var/lib/lahari/visits.json"
DEFAULT_PORT = 8083
DEFAULT_HOST = "127.0.0.1"


def make_handler(store: CounterStore):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/api/visits":
                self._json(200, {"count": store.increment_and_get()})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            self._json(405, {"error": "method not allowed"})

        def log_message(self, format: str, *args) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    return Handler


def main() -> None:
    counter_path = os.environ.get("LAHARI_COUNTER_PATH", DEFAULT_COUNTER_PATH)
    port = int(os.environ.get("LAHARI_COUNTER_PORT", DEFAULT_PORT))
    host = os.environ.get("LAHARI_COUNTER_HOST", DEFAULT_HOST)

    store = CounterStore(counter_path)
    server = ThreadingHTTPServer((host, port), make_handler(store))
    print(f"lahari-counter listening on {host}:{port}, counter file {counter_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
