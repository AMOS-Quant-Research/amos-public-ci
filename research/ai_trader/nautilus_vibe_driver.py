"""Execute a Vibe SignalEngine on XAUUSD Raw Bid/Ask through Nautilus.

Signals are calculated from internal M1 bars made only from the supplied quote
stream.  Orders are submitted on the next quote and are filled by Nautilus;
no OHLC execution path exists in this driver.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.models import FixedFeeModel
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig, RiskEngineConfig
from nautilus_trader.model import BarType, Money
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Quantity
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.trading.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy


def _load_signal(path: Path):
    spec = importlib.util.spec_from_file_location("vibe_signal_engine", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load Vibe signal_engine.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = getattr(module, "SignalEngine", None)
    if engine is None:
        raise ValueError("SignalEngine class not found")
    return engine()


def _f(value) -> float:
    return float(value.as_double()) if hasattr(value, "as_double") else float(value)


def _bars(ticks: list[QuoteTick]) -> pd.DataFrame:
    rows = [(pd.Timestamp(int(t.ts_event), unit="ns", tz="UTC"), _f(t.bid_price), _f(t.ask_price)) for t in ticks]
    frame = pd.DataFrame(rows, columns=["timestamp", "bid", "ask"]).set_index("timestamp")
    mid = (frame["bid"] + frame["ask"]) / 2
    # Nautilus INTERNAL bars carry the event minute, not a synthetic next-bar
    # label. Keep the signal index at that same minute so a decision made from
    # completed raw ticks is submitted on the following quote.
    out = mid.resample("1min", label="left", closed="left").ohlc().dropna()
    out["bid"] = frame["bid"].resample("1min", label="left", closed="left").last().reindex(out.index)
    out["ask"] = frame["ask"].resample("1min", label="left", closed="left").last().reindex(out.index)
    out["volume"] = 1.0
    return out


def _executable_l1(raw_ticks: list[QuoteTick], depth_units: int = 1000) -> tuple[list[QuoteTick], int]:
    """Keep every raw price/timestamp; supply only missing executable L1 size."""
    depth = Quantity.from_int(depth_units)
    out, replaced = [], 0
    for tick in raw_ticks:
        if _f(tick.bid_size) <= 0 or _f(tick.ask_size) <= 0:
            out.append(QuoteTick(instrument_id=tick.instrument_id, bid_price=tick.bid_price, ask_price=tick.ask_price,
                                 bid_size=depth if _f(tick.bid_size) <= 0 else tick.bid_size,
                                 ask_size=depth if _f(tick.ask_size) <= 0 else tick.ask_size,
                                 ts_event=tick.ts_event, ts_init=tick.ts_init))
            replaced += 1
        else:
            out.append(tick)
    return out, replaced


class _Config(StrategyConfig, frozen=True):
    instrument_id: object
    bar_type: object
    quantity: Decimal
    signals: dict[int, float]


class _VibeRawTickStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.target = 0.0
        self.entries = 0
        self.bar_events = 0
        self.matched_signals = 0
        self.order_pending = False

    def on_start(self):
        self.subscribe_quote_ticks(self.config.instrument_id)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar):
        self.bar_events += 1
        if int(bar.ts_event) // 60_000_000_000 in self.config.signals:
            self.matched_signals += 1
        self.target = float(self.config.signals.get(int(bar.ts_event) // 60_000_000_000, 0.0))

    def on_quote_tick(self, tick):
        if self.order_pending:
            return
        long = self.portfolio.is_net_long(self.config.instrument_id)
        short = self.portfolio.is_net_short(self.config.instrument_id)
        if abs(self.target) < 1e-12:
            if long or short:
                self.close_all_positions(self.config.instrument_id)
            return
        wanted_long = self.target > 0
        if (wanted_long and short) or ((not wanted_long) and long):
            self.close_all_positions(self.config.instrument_id)
            return
        if (wanted_long and not long) or ((not wanted_long) and not short):
            inst = self.cache.instrument(self.config.instrument_id)
            order = self.order_factory.market(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.BUY if wanted_long else OrderSide.SELL,
                quantity=inst.make_qty(self.config.quantity),
            )
            self.submit_order(order)
            self.order_pending = True
            self.entries += 1

    def on_order_filled(self, event):
        self.order_pending = False

    def on_order_rejected(self, event):
        self.order_pending = False

    def on_order_canceled(self, event):
        self.order_pending = False

    def on_stop(self):
        self.close_all_positions(self.config.instrument_id)


def _metric(pnls: np.ndarray) -> dict[str, float | None]:
    wins, losses = pnls[pnls > 0], pnls[pnls < 0]
    pf = float(wins.sum() / abs(losses.sum())) if len(losses) else None
    equity = np.r_[0.0, np.cumsum(pnls)]
    dd = float(np.max(np.maximum.accumulate(equity) - equity))
    return {"PF": pf, "EV": float(pnls.mean()) if len(pnls) else 0.0, "MaxDD": dd,
            "MAE": None, "MFE": None}


def _execution_profile(spec: dict, fallback: dict) -> tuple[dict, str | None]:
    """Load only a broker-log calibrated profile; otherwise retain assumptions."""
    path = spec.get("execution_profile_path")
    if not path:
        return dict(fallback), None
    raw = Path(str(path)).read_bytes()
    profile = json.loads(raw)
    required = {"status", "symbol", "commission_per_lot_usd", "slippage_probability",
                "margin_rate", "max_leverage", "sample_size"}
    if not required.issubset(profile) or profile.get("status") != "CALIBRATED_FROM_BROKER_LOGS":
        raise ValueError("execution profile must be CALIBRATED_FROM_BROKER_LOGS with all required fields")
    if profile.get("symbol") != "XAUUSD" or int(profile["sample_size"]) < 100:
        raise ValueError("execution profile must contain at least 100 XAUUSD broker fills")
    merged = dict(fallback)
    merged.update({key: profile[key] for key in ("commission_per_lot_usd", "margin_rate", "max_leverage")})
    merged["slippage_probability"] = float(profile["slippage_probability"])
    return merged, hashlib.sha256(raw).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vibe-run-dir", required=True)
    ap.add_argument("--vibe-request", required=True)
    ap.add_argument("--vibe-evidence", required=True)
    args = ap.parse_args()
    run_dir = Path(args.vibe_run_dir)
    request = json.loads(Path(args.vibe_request).read_text(encoding="utf-8"))
    config = request["config"]
    spec = config["nautilus_rawtick"]
    catalog = ParquetDataCatalog(str(spec["catalog_path"]))
    instrument = next((x for x in catalog.instruments() if x.id.symbol.value.replace("/", "") == "XAUUSD"), None)
    if instrument is None:
        raise SystemExit("XAUUSD instrument missing from Raw Bid/Ask catalog")
    raw_ticks = catalog.query(data_cls=QuoteTick, identifiers=[instrument.id.value])
    if not raw_ticks:
        raise SystemExit("no XAUUSD Raw Bid/Ask ticks")
    ticks, l1_replacements = _executable_l1(raw_ticks)
    bars = _bars(ticks)
    signal_engine = _load_signal(run_dir / "code" / "signal_engine.py")
    generated = signal_engine.generate({"XAUUSD": bars})
    series = generated.get("XAUUSD")
    if not isinstance(series, pd.Series):
        raise SystemExit("SignalEngine must return a pandas Series for XAUUSD")
    signals = {int((pd.Timestamp(ts).tz_convert("UTC").value if pd.Timestamp(ts).tzinfo else pd.Timestamp(ts, tz="UTC").value) // 60_000_000_000): float(v)
               for ts, v in series.dropna().items() if np.isfinite(float(v))}
    cost, profile_hash = _execution_profile(dict(spec), dict(spec["cost_model"]))
    commission = float(cost["commission_per_lot_usd"]) * float(spec.get("lots", 0.01)) / 2.0
    engine = BacktestEngine(config=BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR", bypass_logging=True), risk_engine=RiskEngineConfig(bypass=True)))
    fee_model = FixedFeeModel(Money(commission, USD)) if commission > 0 else None
    fill_model = FillModel(prob_slippage=float(cost.get("slippage_probability", 0.0)), random_seed=42)
    engine.add_venue(venue=instrument.id.venue, oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
                     base_currency=USD, starting_balances=[Money(float(spec.get("initial_cash", 10000)), USD)],
                     default_leverage=Decimal(str(cost["max_leverage"])), fee_model=fee_model, fill_model=fill_model)
    engine.add_instrument(instrument); engine.add_data(ticks)
    bar_type = BarType.from_str(f"{instrument.id.value}-1-MINUTE-BID-INTERNAL")
    strategy = _VibeRawTickStrategy(_Config(instrument_id=instrument.id, bar_type=bar_type,
                                              quantity=Decimal(str(spec.get("trade_units", 1))), signals=signals))
    engine.add_strategy(strategy); engine.run(); report = engine.trader.generate_positions_report()
    orders_report = engine.trader.generate_orders_report()
    fills_report = engine.trader.generate_fills_report()
    pnls = np.array([float(str(v).split()[0]) for v in report.get("realized_pnl", [])], dtype=float) if report is not None else np.array([])
    evidence = {"contract": "amos.vibe.measured-evidence.v1", "live_trading": False,
                "engine": "NautilusTrader BacktestEngine", "ohlc_resample_used": False,
                "raw_ticks": len(raw_ticks), "native_fills": int(len(pnls)), "kpis": _metric(pnls),
                "diagnostics": {"signal_minutes": len(signals), "internal_bars": strategy.bar_events,
                                "matched_signal_bars": strategy.matched_signals, "orders_submitted": strategy.entries,
                                "synthetic_l1_size_replacements": l1_replacements,
                                "orders_report_rows": 0 if orders_report is None else len(orders_report),
                                "fills_report_rows": 0 if fills_report is None else len(fills_report),
                                "order_status": [] if orders_report is None or "status" not in orders_report else orders_report["status"].value_counts().to_dict(),
                                "first_order": None if orders_report is None or orders_report.empty else json.loads(orders_report.iloc[0].to_json(date_format="iso"))},
                "cost_model": {"commission_applied": commission, "spread": "native_bid_ask",
                               "slippage_points_per_side": cost["slippage_points_per_side"],
                               "slippage_probability": cost.get("slippage_probability", 0.0),
                               "margin_rate": cost["margin_rate"],
                               "execution_profile_hash": profile_hash,
                               "execution_profile_status": "CALIBRATED" if profile_hash else "ASSUMPTION_ONLY"}}
    Path(args.vibe_evidence).write_text(json.dumps(evidence, indent=2, allow_nan=False), encoding="utf-8")
    engine.dispose()


if __name__ == "__main__":
    main()
