import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from research.dagram.vibe_signal_bridge import SignalEngine

class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"observations.json"
        self.idx=pd.date_range("2026-10-01T00:00:00Z",periods=5,freq="min")
        self.bars={"XAUUSD":pd.DataFrame({"close":[1,2,3,4,5]},index=self.idx)}
    def test_causal_signals(self):
        self.path.write_text(json.dumps([
            {"issuedAt":"2026-10-01T00:00:10Z","side":"LONG"},
            {"issuedAt":"2026-10-01T00:02:10Z","side":"SHORT"},
            {"issuedAt":"2026-10-01T00:03:10Z","plan":None}
        ]))
        with patch.dict(os.environ,{"AMOS_DAGRAM_OBSERVATIONS":str(self.path)}):
            got=SignalEngine().generate(self.bars)["XAUUSD"].tolist()
        self.assertEqual(got,[0,1,1,-1,0])
    def test_missing_observations_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            SignalEngine(str(self.path)).generate(self.bars)
    def test_invalid_side_fails(self):
        self.path.write_text(json.dumps([{"issuedAt":"2026-10-01T00:00:10Z","side":"UNKNOWN"}]))
        with self.assertRaises(ValueError):
            SignalEngine(str(self.path)).generate(self.bars)
if __name__=="__main__":unittest.main()
