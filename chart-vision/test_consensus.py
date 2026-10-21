import unittest
from consensus import summarize
class ConsensusTest(unittest.TestCase):
 def test_all_agree(self):
  r={str(i):{"status":"OK","report":"BUY"} for i in range(5)}
  self.assertEqual(summarize(r)["decision"],"BUY")
 def test_missing_does_not_vote(self):
  r={"a":{"status":"OK","report":"BUY"},"b":{"status":"NOT_CONFIGURED"}}
  self.assertEqual(summarize(r)["decision"],"MIXED")
  self.assertEqual(summarize(r)["participating"],1)
 def test_conflicting_vote(self):
  r={"a":{"status":"OK","report":"SELL"},"b":{"status":"OK","report":"BUY"}}
  self.assertEqual(summarize(r)["decision"],"MIXED")
 def test_no_vote(self):
  self.assertEqual(summarize({"a":{"status":"ERROR"}})["decision"],"INSUFFICIENT_DATA")
 def test_ambiguous_text(self):
  self.assertEqual(summarize({"a":{"status":"OK","report":"BUY or SELL"}})["participating"],0)
if __name__=="__main__":unittest.main()
