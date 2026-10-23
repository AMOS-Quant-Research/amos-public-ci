import json
import tempfile
import unittest
from pathlib import Path
from adapter import normalize_trades, export_json, export_csv

SAMPLE = {"trade_id":"T1","symbol":"XAUUSD","side":"buy","entry_time":"2026-10-01T00:00:00Z","exit_time":"2026-10-01T00:01:00Z","entry_price":2600,"exit_price":2601,"quantity":0.01,"net_pnl":1.0}

class AdapterTest(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_trades([SAMPLE])[0]["side"], "BUY")
    def test_invalid(self):
        with self.assertRaises(ValueError):
            normalize_trades([dict(SAMPLE, quantity=0)])
    def test_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            j = Path(temp)/"trades.json"
            c = Path(temp)/"trades.csv"
            self.assertEqual(export_json([SAMPLE], j), 1)
            self.assertEqual(export_csv([SAMPLE], c), 1)
            self.assertEqual(json.loads(j.read_text())["trades"][0]["trade_id"], "T1")
            self.assertIn("trade_id", c.read_text())
if __name__ == "__main__":
    unittest.main()
