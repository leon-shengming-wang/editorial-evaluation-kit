"""Loopback-only, stateless review service. No uploads are persisted."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .core import InputError, MAX_BYTES, analyze, parse, strict_loads
ROOT = Path(__file__).resolve().parent.parent

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, data, mime='application/json'):
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def allowed(self):
        host = self.headers.get('Host', '')
        valid = {'127.0.0.1:%d' % self.server.server_port, 'localhost:%d' % self.server.server_port}
        origin = self.headers.get('Origin')
        return host in valid and (origin is None or origin == 'http://' + host)

    def do_GET(self):
        if not self.allowed():
            return self.respond(403, {'error': 'Use the local URL printed by the server.'})
        if self.path in ('/', '/index.html'):
            return self.respond(200, (ROOT / 'static/index.html').read_bytes(), 'text/html')
        if self.path == '/api/demo':
            return self.respond(200, json.loads((ROOT / 'examples/demo.json').read_text()))
        self.respond(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.allowed():
            return self.respond(403, {'error': 'Cross-origin requests are not allowed.'})
        if self.path != '/api/analyze':
            return self.respond(404, {'error': 'Not found'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.respond(415, {'error': 'Use application/json.'})
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if not 0 < n <= MAX_BYTES:
                return self.respond(413, {'error': 'Request must be between 1 byte and 2 MB.'})
            self.connection.settimeout(10)
            raw = self.rfile.read(n)
            if len(raw) != n:
                raise InputError('Incomplete request.')
            body = strict_loads(raw)
            if not isinstance(body, dict) or set(body) not in ({'cases'}, {'text'}):
                raise InputError('Expected an object containing only cases or text.')
            if 'text' in body and not isinstance(body['text'], str):
                raise InputError('text must be a string.')
            self.respond(200, analyze(parse(body['text']) if 'text' in body else body['cases']))
        except (ValueError, UnicodeError, RecursionError, TimeoutError) as exc:
            self.respond(400, {'error': str(exc) if isinstance(exc, InputError) else 'Invalid JSON request.'})

def serve(port):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print('CompareKit: http://127.0.0.1:%d — Ctrl-C to stop. No input is saved on the server.' % server.server_port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
