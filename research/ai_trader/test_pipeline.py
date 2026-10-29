import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research.ai_trader.pipeline import run

class PipelineTests(unittest.TestCase):
    def test_pipeline_fails_closed_on_missing_catalog(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((ImportError,ModuleNotFoundError,ValueError,FileNotFoundError)):
                run(Path(d)/"nonexistent",Path(d)/"output")
