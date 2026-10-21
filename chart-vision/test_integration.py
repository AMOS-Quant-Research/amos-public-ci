"""HTTP integration tests: mock upstreams, no real AI claims."""
import base64, http.client, json, threading, unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import app

PNG=b"\x89PNG\r\n\x1a\n"+b"mock-image-bytes"
class Integration(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(("127.0.0.1",0),app.Handler)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
  cls.thread.start()
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def request(self,path,payload=None):
  c=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=10)
  if payload is None:c.request("GET",path)
  else:c.request("POST",path,json.dumps(payload),{"Content-Type":"application/json"})
  r=c.getresponse();data=r.read();status=r.status;c.close();return status,data
 def test_ui_served(self):
  status,body=self.request("/")
  self.assertEqual(status,200);self.assertIn(b"AMOS Chart Vision",body)
 def test_five_parallel_http(self):
  with patch.object(app,"run_one",side_effect=lambda name,raw:{"status":"OK","report":name}):
   status,body=self.request("/analyze",{"image_base64":base64.b64encode(PNG).decode()})
  result=json.loads(body)
  self.assertEqual(status,200);self.assertEqual(len(result["results"]),5)
  self.assertEqual([result["results"][k]["report"] for k in app.ENGINES],list(app.ENGINES))
 def test_invalid_image(self):
  status,body=self.request("/analyze",{"image_base64":base64.b64encode(b"not-image").decode()})
  self.assertEqual(status,400)
 def test_bad_base64(self):
  status,body=self.request("/analyze",{"image_base64":"***"})
  self.assertEqual(status,400)
 def test_unknown_route(self):
  status,_=self.request("/unknown");self.assertEqual(status,404)
if __name__=="__main__":unittest.main()
