import json
import sys
import tempfile
import unittest
from pathlib import Path

from backtest.engines.nautilus_rawtick import run_nautilus_rawtick


def _config(driver: Path) -> dict:
    return {
        "codes": ["XAUUSD"], "start_date": "2026-07-27", "end_date": "2026-07-31",
        "source": "auto", "interval": "1m", "engine": "nautilus_rawtick",
        "nautilus_rawtick": {
            "driver_command": [sys.executable, str(driver)],
            "cost_model": {"commission_per_lot_usd": 7, "slippage_points_per_side": 2,
                           "contract_size": 100, "margin_rate": 0.005},
        },
    }


class NautilusRawTickAdapterTest(unittest.TestCase):
    def test_rawtick_adapter_writes_standard_vibe_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "code").mkdir()
            (tmp_path / "code" / "signal_engine.py").write_text("class SignalEngine: pass\n")
            (tmp_path / "config.json").write_text(json.dumps(_config(tmp_path / "driver.py")))
            driver = tmp_path / "driver.py"
            driver.write_text(
        "import argparse,json\n"
        "p=argparse.ArgumentParser();p.add_argument('--vibe-run-dir');p.add_argument('--vibe-request');p.add_argument('--vibe-evidence');a=p.parse_args()\n"
        "json.dump({'contract':'amos.vibe.measured-evidence.v1','engine':'NautilusTrader BacktestEngine',"
        "'ohlc_resample_used':False,'raw_ticks':8,'native_fills':2,"
        "'kpis':{'PF':1.2,'EV':3.4,'MaxDD':5.6,'MAE':1.0,'MFE':2.0},'trades':[]},open(a.vibe_evidence,'w'))\n"
            )
            metrics = run_nautilus_rawtick(_config(driver), tmp_path)
            self.assertEqual(metrics["verification_level"], "RAW_BIDASK_NAUTILUS")
            self.assertTrue((tmp_path / "artifacts" / "metrics.csv").exists())
            self.assertTrue((tmp_path / "run_card.json").exists())


    def test_rawtick_adapter_rejects_ohlc_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "code").mkdir()
            (tmp_path / "code" / "signal_engine.py").write_text("class SignalEngine: pass\n")
            driver = tmp_path / "driver.py"
            driver.write_text(
        "import argparse,json\n"
        "p=argparse.ArgumentParser();p.add_argument('--vibe-run-dir');p.add_argument('--vibe-request');p.add_argument('--vibe-evidence');a=p.parse_args()\n"
        "json.dump({'contract':'amos.vibe.measured-evidence.v1','engine':'NautilusTrader BacktestEngine',"
        "'ohlc_resample_used':True,'raw_ticks':8,'native_fills':2,"
        "'kpis':{'PF':1,'EV':1,'MaxDD':1,'MAE':1,'MFE':1}},open(a.vibe_evidence,'w'))\n"
            )
            with self.assertRaisesRegex(ValueError, "Raw Bid/Ask"):
                run_nautilus_rawtick(_config(driver), tmp_path)
