"""Independent Nautilus cells. Parallelism never fuses books or invents fills.

A cell is one book on one instrument. MAIN and RAGE that share a scenario id
are a pair: they may run on different runners, and they are joined afterwards.
They are not one backtest. Raw catalog cells stay blocked until a real
bid/ask catalog is passed. OHLC is not a cell.
"""

from __future__ import annotations

from dataclasses import dataclass

from adapters.nautilus.fills import native_fill_count

# Three at a time is only a proposal. Issue #42 says the number is fixed
# after runner capacity is measured. It has not been measured.
PROPOSED_PUBLIC_PARALLEL = 3
PARALLEL_CAP_STATUS = "NOT_VERIFIED"
PUBLIC_MAX_PARALLEL = PROPOSED_PUBLIC_PARALLEL

# rc6 removed nautilus_trader.backtest.models. The public smoke failed on that path.
FEE_MODEL_IMPORT = "nautilus_trader.execution.MakerTakerFeeModel"
BROKEN_FEE_MODEL_IMPORT = "nautilus_trader.backtest.models.MakerTakerFeeModel"

RAW_INSTRUMENTS = ("XAUUSD", "USDJPY", "EURUSD", "GBPUSD", "XAGUSD")
BOOKS = ("MAIN", "RAGE", "MULTI")


@dataclass(frozen=True)
class BtCell:
    cell_id: str
    scenario_id: str
    book: str
    instrument: str
    data_kind: str
    runner: str
    status: str

    def as_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "scenario_id": self.scenario_id,
            "book": self.book,
            "instrument": self.instrument,
            "data_kind": self.data_kind,
            "runner": self.runner,
            "status": self.status,
            "nautilus_native_fills": native_fill_count(),
            "market_kpi": None,
            "ohlc_proxy": False,
            "fee_model_import": FEE_MODEL_IMPORT,
        }


def build_cells() -> tuple[BtCell, ...]:
    cells: list[BtCell] = []
    for book in BOOKS:
        cells.append(
            BtCell(
                cell_id=f"syn-xau-{book.lower()}",
                scenario_id="syn-xau-wire",
                book=book,
                instrument="XAUUSD",
                data_kind="SYNTHETIC_QUOTE",
                runner="public",
                status="SYNTHETIC_ONLY",
            )
        )
    for instrument in RAW_INSTRUMENTS:
        for book in BOOKS:
            cells.append(
                BtCell(
                    cell_id=f"raw-{instrument.lower()}-{book.lower()}",
                    scenario_id=f"raw-{instrument}",
                    book=book,
                    instrument=instrument,
                    data_kind="RAW_BIDASK",
                    runner="external",
                    status="BLOCKED_NO_CATALOG",
                )
            )
    return tuple(cells)


def shard_cells(cells: tuple[BtCell, ...] | list[BtCell], groups: int) -> tuple[tuple[BtCell, ...], ...]:
    if groups < 1:
        raise ValueError("groups must be >= 1")
    buckets: list[list[BtCell]] = [[] for _ in range(groups)]
    for index, cell in enumerate(cells):
        buckets[index % groups].append(cell)
    return tuple(tuple(bucket) for bucket in buckets)


def paired(cells: tuple[BtCell, ...] | list[BtCell]) -> dict[str, tuple[str, ...]]:
    found: dict[str, list[str]] = {}
    for cell in cells:
        found.setdefault(cell.scenario_id, []).append(cell.book)
    return {key: tuple(sorted(books)) for key, books in sorted(found.items())}
