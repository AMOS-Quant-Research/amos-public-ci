"""Patch the pinned MIT Vibe native driver to honor research-only fractional sizing.

Strict source fingerprint/anchors; abort on unexpected upstream changes.
No live-trading path. Native BacktestEngine only.
"""
from pathlib import Path
import hashlib
import sys

EXPECTED_SHA256 = None  # original ZIP SHA-256 is checked by caller

def patch(source: Path, dest: Path):
    text = source.read_text(encoding="utf-8")
    replacements = [
        ("    signals: dict[int, float]\n",
         "    signals: dict[int, float]\n    paper_sizing_enabled: bool = False\n"),
        ("        self.order_pending = False\n\n    def on_start",
         "        self.order_pending = False\n        self.fractional_size_orders = 0\n        self.sizing_rejections = 0\n\n    def on_start"),
        ("""            order = self.order_factory.market(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.BUY if wanted_long else OrderSide.SELL,
                quantity=inst.make_qty(self.config.quantity),
            )""",
         """            if self.config.paper_sizing_enabled:
                fraction = min(1.0, max(0.0, abs(self.target)))
                if fraction < 1.0:
                    self.fractional_size_orders += 1
                qty = inst.make_qty(self.config.quantity * Decimal(str(fraction)))
                if _f(qty) <= 0 or (inst.min_quantity is not None and qty < inst.min_quantity):
                    self.sizing_rejections += 1
                    return
            else:
                qty = inst.make_qty(self.config.quantity)
            order = self.order_factory.market(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.BUY if wanted_long else OrderSide.SELL,
                quantity=qty,
            )"""),
        ('quantity=Decimal(str(spec.get("trade_units", 1))), signals=signals))',
         'quantity=Decimal(str(spec.get("trade_units", 1))), signals=signals,\n'
         '                                              paper_sizing_enabled=bool(spec.get("paper_sizing_enabled", False))))'),
        ('"orders_submitted": strategy.entries,',
         '"orders_submitted": strategy.entries,\n'
         '                                "paper_sizing_enabled": bool(spec.get("paper_sizing_enabled", False)),\n'
         '                                "fractional_size_orders": strategy.fractional_size_orders,\n'
         '                                "sizing_rejections": strategy.sizing_rejections,'),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError(f"upstream Vibe driver drift: {old[:65]!r} matches={text.count(old)}")
        text = text.replace(old, new, 1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()

if __name__ == "__main__":
    print(patch(Path(sys.argv[1]), Path(sys.argv[2])))
