import http.client, json, threading, unittest
from http.server import HTTPServer
from claimcheck.server import Handler, TOKEN


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path="/", data=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        h = {"Content-Type": "application/json", "X-CSRF-Token": TOKEN}
        h.update(headers or {})
        c.request(method, path, json.dumps(data) if data is not None else None, h)
        r = c.getresponse()
        result = (r.status, r.read(), dict(r.getheaders()))
        c.close()
        return result

    def test_get(self):
        s, b, h = self.request("GET")
        self.assertEqual(s, 200)
        self.assertIn(b"LEDGER", b)
        self.assertEqual(h["X-Frame-Options"], "DENY")

    def test_get_bad_host(self):
        self.assertEqual(self.request("GET", headers={"Host": "evil.invalid"})[0], 403)

    def test_post_bad_origin(self):
        self.assertEqual(
            self.request("POST", "/analyze", {}, {"Origin": "https://evil.invalid"})[0],
            403,
        )

    def test_post_bad_token(self):
        self.assertEqual(
            self.request("POST", "/analyze", {}, {"X-CSRF-Token": "bad"})[0], 403
        )

    def test_no_arbitrary_fetch(self):
        self.assertEqual(
            self.request("POST", "/fetch", {"url": "http://127.0.0.1"})[0], 404
        )

    def test_analyze(self):
        s, b, _ = self.request(
            "POST",
            "/analyze",
            {"response": "Alpha was founded in 2020.", "sources": []},
        )
        self.assertEqual(s, 200)
        self.assertEqual(json.loads(b)["claims"][0]["verdict"], "unreviewed")

    def test_discovery_no_consent(self):
        self.assertEqual(
            self.request("POST", "/discover", {"query": "NASA", "consent": False})[0],
            400,
        )

    def test_input_invalid(self):
        self.assertEqual(self.request("POST", "/analyze", {"response": False})[0], 400)

    def test_path_traversal(self):
        self.assertEqual(self.request("GET", "/../../README.md")[0], 404)
