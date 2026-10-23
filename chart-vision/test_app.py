import base64,unittest
from unittest.mock import patch
import app
class TestChartVision(unittest.TestCase):
 def test_slots(self):
  self.assertEqual(len(app.ENGINES),5)
 def test_empty_rejected(self):
  with self.assertRaises(ValueError):app.analyze(b"")
 def test_not_configured(self):
  with patch.dict("os.environ",{},clear=True):
   self.assertEqual(app.run_one("screenchart",b"test")["status"],"NOT_CONFIGURED")
 def test_parallel_results(self):
  with patch.object(app,"run_one",return_value={"status":"NOT_CONFIGURED"}):
   self.assertEqual(len(app.analyze(b"test")["results"]),5)
if __name__=="__main__":unittest.main()
