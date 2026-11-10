#!/usr/bin/env python3
"""Serve only the two public extension artifacts, on IPv4 loopback."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path("/usr/local/share/chrome-venus/web")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        name = urlsplit(self.path).path
        types = {"/updates.xml": "application/xml", "/youtube-codecs.crx": "application/x-chrome-extension"}
        if name not in types:
            self.send_error(404)
            return
        data = (ROOT / name.lstrip("/")).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", types[name])
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 18765), Handler).serve_forever()
