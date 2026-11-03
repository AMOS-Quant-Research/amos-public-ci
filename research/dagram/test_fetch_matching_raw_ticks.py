import json
import lzma
import struct
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from research.dagram.fetch_matching_raw_ticks import get_day


class FetchTests(unittest.TestCase):
    def test_complete_day_and_bid_ask(self):
        record = lzma.compress(struct.pack(">3I2f", 1000, 4069000, 4068000, 1.5, 2.5))
        with tempfile.TemporaryDirectory() as td:
            result = get_day(datetime(2026, 10, 29, tzinfo=timezone.utc), td, fetch=lambda url: record)
            self.assertTrue(result["complete"])
            self.assertEqual(result["ticks"], 24)
            self.assertIn("4068.00000,4069.00000", Path(td, "xauusd-2026-10-29-bidask.csv").read_text())

    def test_missing_hour_blocks_partial_file(self):
        with tempfile.TemporaryDirectory() as td:
            def fail(url):
                raise OSError("missing")
            result = get_day(datetime(2026, 10, 29, tzinfo=timezone.utc), td, fetch=fail)
            self.assertFalse(result["complete"])
            self.assertFalse(Path(td, "xauusd-2026-10-29-bidask.csv").exists())


if __name__ == "__main__":
    unittest.main()
