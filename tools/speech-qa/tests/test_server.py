import http.client
import threading
import unittest
from http.server import HTTPServer
from speechqa.server import Handler


class ServerChecks(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path="/", body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request(method, path, body, headers or {})
        r = c.getresponse()
        status = r.status
        data = r.read()
        c.close()
        return status, data

    def test_get(self):
        status, data = self.request("GET")
        self.assertEqual(status, 200)
        self.assertIn(b'type="file"', data)

    def test_bad_path(self):
        self.assertEqual(self.request("GET", "/private")[0], 404)

    def test_no_body(self):
        self.assertEqual(self.request("POST")[0], 413)

    def test_foreign_origin(self):
        self.assertEqual(
            self.request("POST", headers={"Origin": "http://evil.invalid"})[0], 403
        )

    def test_rebound_host(self):
        self.assertEqual(self.request("POST", headers={"Host": "evil.invalid"})[0], 403)

    def test_wrong_content_type(self):
        self.assertEqual(
            self.request(
                "POST", body=b"x", headers={"Content-Type": "application/json"}
            )[0],
            400,
        )

    def test_bad_token(self):
        body = b'--x\r\nContent-Disposition: form-data; name="token"\r\n\r\nbad\r\n--x--\r\n'
        self.assertEqual(
            self.request(
                "POST",
                body=body,
                headers={"Content-Type": "multipart/form-data; boundary=x"},
            )[0],
            403,
        )

    def test_rebound_get_host(self):
        self.assertEqual(self.request("GET", headers={"Host": "evil.invalid"})[0], 403)

    def test_cross_origin_get(self):
        self.assertEqual(
            self.request("GET", headers={"Origin": "http://evil.invalid"})[0], 403
        )
