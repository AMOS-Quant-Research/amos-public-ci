import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research.ai_trader.native_run import DEFAULT,SOURCE,run

class NativeBridgeTests(unittest.TestCase):
    def test_generated_strategy_compiles(self):
        source=SOURCE.replace("__PARAMS__",repr(DEFAULT))
        compile(source,"signal_engine.py","exec")
        self.assertIn("class SignalEngine",source)
        self.assertIn("decide(inputs,PARAMS)",source)
    def test_missing_catalog_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                run(Path(d)/"missing",Path(d)/"out")
    def test_no_native_evidence_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            catalog=root/"catalog"
            catalog.mkdir()
            class Result:
                returncode=0
                stdout=""
                stderr=""
            with patch("research.ai_trader.native_run.subprocess.run",return_value=Result()):
                with self.assertRaisesRegex(RuntimeError,"NATIVE_BT_FAILED"):
                    run(catalog,root/"output")
    def test_native_fill_report_proof_required(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            catalog=root/"catalog"
            catalog.mkdir()
            class Result:
                returncode=0
                stdout=""
                stderr=""
            def fake_run(args,**kwargs):
                path=Path(args[args.index("--vibe-evidence")+1])
                path.write_text(json.dumps({"engine":"NautilusTrader BacktestEngine",
                    "ohlc_resample_used":False,"raw_ticks":208501,
                    "diagnostics":{"fills_report_rows":0}}))
                return Result()
            with patch("research.ai_trader.native_run.subprocess.run",side_effect=fake_run):
                with self.assertRaisesRegex(ValueError,"zero fills"):
                    run(catalog,root/"output")
    def test_nim_missing_secret_fails_before_driver(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            catalog=root/"catalog"
            catalog.mkdir()
            with patch.dict("os.environ",{"NVIDIA_NIM_API_KEY":""}):
                with self.assertRaisesRegex(RuntimeError,"NIM_SECRET_MISSING"):
                    run(catalog,root/"output",nim=True)
