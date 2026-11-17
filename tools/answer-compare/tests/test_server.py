import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from comparekit.server import Handler
from test_core import case

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def request(self,path='/api/analyze',data=None,headers=None,method='POST'):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        h={'Content-Type':'application/json'}; h.update(headers or {})
        c.request(method,path,json.dumps(data or {'cases':[case()]}),h)
        r=c.getresponse(); status=r.status; raw=r.read(); c.close(); return status,raw
    def test_analyze(self): self.assertEqual(self.request()[0],200)
    def test_host_guard(self): self.assertEqual(self.request(headers={'Host':'evil.example'})[0],403)
    def test_origin_guard(self): self.assertEqual(self.request(headers={'Origin':'https://evil.example'})[0],403)
    def test_type_guard(self): self.assertEqual(self.request(headers={'Content-Type':'text/plain'})[0],415)
    def test_unknown_path(self): self.assertEqual(self.request('/nope')[0],404)
    def test_invalid(self): self.assertEqual(self.request(data={'other':[]})[0],400)
    def test_demo(self):
        s,b=self.request('/api/demo',method='GET'); self.assertEqual(s,200); self.assertEqual(len(json.loads(b)['cases']),8)
    def test_home(self): self.assertEqual(self.request('/',method='GET')[0],200)
    def test_traversal(self): self.assertEqual(self.request('/../comparekit/core.py',method='GET')[0],404)

if __name__=='__main__': unittest.main()
