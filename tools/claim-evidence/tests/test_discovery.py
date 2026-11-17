import unittest
from claimcheck.discovery import discover


class DiscoveryTests(unittest.TestCase):
    def test_requires_explicit_consent(self):
        for value in [False, None, "true", 1]:
            with self.assertRaises(ValueError):
                discover("NASA", value, lambda *x: self.fail("must not fetch"))

    def test_limits(self):
        for q in ["", None, "x" * 161, "a\nb"]:
            with self.assertRaises(ValueError):
                discover(q, True, lambda *x: self.fail("must not fetch"))

    def test_fixed_encoded_path(self):
        calls = []

        def fetch(path, params=None):
            calls.append((path, params))
            return (
                {"pages": [{"key": "//evil.test/../x?secret"}]}
                if len(calls) == 1
                else {"extract": "Public summary", "title": "Title"}
            )

        r = discover("NASA", True, fetch)
        self.assertEqual(calls[0][0], "/w/rest.php/v1/search/page")
        self.assertEqual(
            calls[1][0], "/api/rest_v1/page/summary/%2F%2Fevil.test%2F..%2Fx%3Fsecret"
        )
        self.assertTrue(
            r["sources"][0]["url"].startswith("https://en.wikipedia.org/wiki/")
        )

    def test_failure_no_fake_source(self):
        def fetch(path, params=None):
            if params:
                return {"pages": [{"key": "NASA"}]}
            raise RuntimeError("offline")

        r = discover("NASA", True, fetch)
        self.assertEqual(r["sources"], [])
        self.assertEqual(len(r["failures"]), 1)

    def test_max_three(self):
        calls = []

        def fetch(path, params=None):
            calls.append(path)
            return (
                {"pages": [{"key": str(i)} for i in range(10)]}
                if params
                else {"extract": "A summary"}
            )

        self.assertEqual(len(discover("NASA", True, fetch)["sources"]), 3)
        self.assertEqual(len(calls), 4)


class TransportTests(unittest.TestCase):
    def fake(self, status=200, chunks=None):
        import types

        class Response:
            status_code = status

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def raise_for_status(self):
                if status != 200:
                    raise ValueError("rejected status")

            def iter_bytes(self):
                return iter(chunks if chunks is not None else [b'{"pages":[]}'])

        class Client:
            def __init__(self, **kwargs):
                assert kwargs["follow_redirects"] is False

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def stream(self, method, url, params=None):
                assert url.startswith("https://en.wikipedia.org/")
                return Response()

        return types.SimpleNamespace(Client=Client)

    def test_redirect_rejected(self):
        import sys
        from unittest.mock import patch
        from claimcheck.discovery import request_json

        with patch.dict(sys.modules, {"httpx": self.fake(302)}):
            with self.assertRaises(ValueError):
                request_json("/w/rest.php/v1/search/page")

    def test_response_size(self):
        import sys
        from unittest.mock import patch
        from claimcheck.discovery import request_json

        with patch.dict(sys.modules, {"httpx": self.fake(chunks=[b"x" * 500001])}):
            with self.assertRaises(ValueError):
                request_json("/w/rest.php/v1/search/page")

    def test_invalid_json(self):
        import sys
        from unittest.mock import patch
        from claimcheck.discovery import request_json

        with patch.dict(sys.modules, {"httpx": self.fake(chunks=[b"not json"])}):
            with self.assertRaises(ValueError):
                request_json("/w/rest.php/v1/search/page")

    def test_no_url_endpoint(self):
        from claimcheck.discovery import request_json

        with self.assertRaises(ValueError):
            request_json("https://evil.invalid/")
