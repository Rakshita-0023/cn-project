#!/usr/bin/env python3
"""Backend A entry point and shared HTTP implementation for both instances."""
import hashlib
import json
import os
import signal
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _common import ROOT, load_network, owned_pid, service_pid_file


# Identical representation on BOTH backends: an ETag remains valid across RR.
CACHE_BODY = b'{"message":"Shared cacheable course-project resource","version":1}\n'
CACHE_ETAG = '"' + hashlib.sha256(CACHE_BODY).hexdigest() + '"'


def etag_matches(value):
    return any(tag.strip().removeprefix("W/") in ("*", CACHE_ETAG)
               for tag in value.split(","))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "CNBackend/1.0"

    def do_GET(self):
        self.respond(head=False)

    def do_HEAD(self):
        self.respond(head=True)

    def respond(self, head):
        path = urlsplit(self.path).path
        backend = self.server.backend
        status, cache, etag = 200, "no-store", None
        if path in ("/cache-demo", "/api/cache"):
            body, cache, etag = CACHE_BODY, "public, max-age=60", CACHE_ETAG
            if etag_matches(self.headers.get("If-None-Match", "")):
                status = 304
        elif path in ("/", "/api/status"):
            data = {"backend": backend, "status": "ok"}
            if path == "/":
                data["message"] = "Computer Networks private service"
            body = (json.dumps(data, sort_keys=True) + "\n").encode()
        else:
            status = 404
            body = b'{"error":"not found"}\n'
        self.send_response(status)
        self.send_header("X-Backend", backend)
        self.send_header("Cache-Control", cache)
        if etag:
            self.send_header("ETag", etag)
        if status != 304:
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head and status != 304:
            self.wfile.write(body)


def serve(backend, port=None, host="0.0.0.0", write_pid=True):
    if port is None:
        key = f"BACKEND_{backend}_PORT"
        port = load_network()[key] if (ROOT / "network.env").is_file() else int(os.environ.get(key, 3001 if backend == "A" else 3002))
    if not 1 <= port <= 65535:
        raise ValueError("Backend port must be between 1 and 65535")
    name = "backend-" + backend.lower()
    if write_pid and owned_pid(name):
        raise ValueError(f"Backend {backend} is already running")
    with ThreadingHTTPServer((host, port), Handler) as server:
        server.backend = backend
        pid = service_pid_file(name)
        if write_pid:
            pid.parent.mkdir(parents=True, exist_ok=True)
            pid.write_text(str(os.getpid()))
        def terminate(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, terminate)
        print(f"Backend {backend}: HTTP/1.1 on {host}:{port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            if write_pid and pid.is_file() and pid.read_text().strip() == str(os.getpid()):
                pid.unlink()


if __name__ == "__main__":
    try:
        serve("A")
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
