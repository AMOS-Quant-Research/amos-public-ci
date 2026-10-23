"""Tests for AutoScope-neutral trade-history envelope."""
import json
import tempfile
import unittest
from pathlib import Path
from integrations.autoscope.nautilus_bridge import convert

class BridgeTests(unittest.TestCase):
    def test_csv_to_json(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "trades.csv"
            dst = Path(d) / "nautilus.json"
            src.write_text("trade_id,symbol,side,entry_time,exit_time,entry_price,exit_price,quantity,net_pnl\n1,XAUUSD,BUY,2026-01-01T00:00:00Z,2026-01-01T00:01:00Z,2700,2701,0.01,1\n", encoding="utf-8")
            self.assertEqual(convert(src, dst), 1)
            obj = json.loads(dst.read_text(encoding="utf-8"))
            self.assertFalse(obj["is_raw_tick"])
            self.assertFalse(obj["execution_verified"])
            self.assertEqual(obj["trades"][0]["symbol"], "XAUUSD")

    def test_invalid_side(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "trades.json"
            src.write_text(json.dumps([{"trade_id": "1", "symbol": "XAUUSD", "side": "HOLD", "entry_time": "x", "exit_time": "y", "entry_price": 1, "exit_price": 2, "quantity": 1, "net_pnl": 1}]))
            with self.assertRaises(ValueError):
                convert(src, Path(d) / "out.json")

if __name__ == "__main__":
    unittest.main()
