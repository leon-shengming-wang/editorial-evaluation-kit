"""Private loopback workbench; no user text is persisted or automatically transmitted."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
from .core import analyze
from .discovery import discover

TOKEN = secrets.token_urlsafe(32)
ROOT = Path(__file__).parent


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def valid_origin(self):
        host = f"127.0.0.1:{self.server.server_port}"
        return self.headers.get("Host") == host and self.headers.get("Origin") in (
            None,
            "http://" + host,
        )

    def reply(self, status, body, mime="application/json; charset=utf-8"):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.valid_origin():
            return self.reply(403, '{"error":"Invalid host or origin"}')
        if self.path == "/":
            return self.reply(
                200,
                (ROOT / "index.html").read_text().replace("CSRF_TOKEN", TOKEN),
                "text/html; charset=utf-8",
            )
        mapping = {
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        if self.path in mapping:
            filename, mime = mapping[self.path]
            return self.reply(200, (ROOT / filename).read_text(), mime)
        if self.path == "/example":
            return self.reply(
                200, (ROOT.parent / "examples/public-demo.json").read_text()
            )
        self.reply(404, '{"error":"Not found"}')

    def do_POST(self):
        if not self.valid_origin():
            return self.reply(403, '{"error":"Invalid host or origin"}')
        if self.headers.get("X-CSRF-Token") != TOKEN:
            return self.reply(403, '{"error":"Reload the workbench"}')
        if self.path not in ("/analyze", "/discover"):
            return self.reply(404, '{"error":"Not found"}')
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 800000:
                raise ValueError("Request must be under 800 KB")
            if self.headers.get("Content-Type") != "application/json":
                raise ValueError("Expected application/json")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")
            if self.path == "/analyze":
                result = analyze(data.get("response"), data.get("sources", []))
            else:
                result = discover(data.get("query"), data.get("consent", False))
            self.reply(200, json.dumps(result, ensure_ascii=False, allow_nan=False))
        except (ValueError, TypeError, KeyError) as error:
            self.reply(400, json.dumps({"error": str(error)}))
        except Exception:
            self.reply(
                502,
                json.dumps(
                    {
                        "error": "Source discovery failed. Check network/dependencies and try again. No substitute evidence was generated; local analysis remains available."
                    }
                ),
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Open http://127.0.0.1:{args.port} (local only)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
