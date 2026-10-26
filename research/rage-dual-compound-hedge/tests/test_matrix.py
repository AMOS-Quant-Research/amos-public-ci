import unittest

from adapters.nautilus.matrix import (
    BROKEN_FEE_MODEL_IMPORT,
    FEE_MODEL_IMPORT,
    PARALLEL_CAP_STATUS,
    PUBLIC_MAX_PARALLEL,
    build_cells,
    paired,
    shard_cells,
)
from adapters.portfolio.synchronized import evaluate


class MatrixTests(unittest.TestCase):
    def test_books_share_a_scenario_and_are_not_one_cell(self):
        cells = build_cells()
        pairs = paired(cells)
        self.assertEqual(pairs["syn-xau-wire"], ("MAIN", "MULTI", "RAGE"))
        self.assertEqual(pairs["raw-XAUUSD"], ("MAIN", "MULTI", "RAGE"))
        self.assertEqual(pairs["raw-USDJPY"], ("MAIN", "MULTI", "RAGE"))
        ids = [cell.cell_id for cell in cells]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(cells), 2)

    def test_raw_cells_stay_blocked_and_synthetic_is_not_a_fill(self):
        for cell in build_cells():
            row = cell.as_dict()
            self.assertIsNone(row["market_kpi"])
            self.assertEqual(row["nautilus_native_fills"], 0)
            self.assertFalse(row["ohlc_proxy"])
            self.assertNotEqual(cell.data_kind, "OHLC")
            if cell.data_kind == "RAW_BIDASK":
                self.assertEqual(cell.status, "BLOCKED_NO_CATALOG")
                self.assertEqual(cell.runner, "external")
            else:
                self.assertEqual(cell.status, "SYNTHETIC_ONLY")

    def test_public_matrix_caps_parallelism_and_covers_every_cell_once(self):
        cells = build_cells()
        shards = shard_cells(cells, PUBLIC_MAX_PARALLEL)
        self.assertEqual(len(shards), PUBLIC_MAX_PARALLEL)
        flat = [cell.cell_id for shard in shards for cell in shard]
        self.assertEqual(sorted(flat), sorted(cell.cell_id for cell in cells))
        wider = shard_cells(cells, PUBLIC_MAX_PARALLEL + 1)
        self.assertEqual(len(wider), PUBLIC_MAX_PARALLEL + 1)
        self.assertEqual(PARALLEL_CAP_STATUS, "NOT_VERIFIED")
        self.assertNotEqual(FEE_MODEL_IMPORT, BROKEN_FEE_MODEL_IMPORT)
        self.assertTrue(FEE_MODEL_IMPORT.startswith("nautilus_trader.execution"))

    def test_issue_42_join_stays_blocked_and_rejects_double_counting(self):
        blocked = evaluate([cell.as_dict() for cell in build_cells()])
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertEqual(blocked["ten_percent"], "NOT_A_PASS")
        self.assertIsNone(blocked["market_kpi"])
        failed = evaluate(
            [
                {
                    "scenario_id": "s",
                    "book": "MAIN",
                    "status": "MEASURED",
                    "monthly_net": [0.01],
                    "transfer_booked_as_profit": True,
                }
            ]
        )
        self.assertEqual(failed["status"], "FAIL")
        joined = evaluate(
            [
                {"scenario_id": "s", "book": book, "status": "MEASURED", "monthly_net": [0.02, -0.01]}
                for book in ("MAIN", "RAGE", "MULTI")
            ]
        )
        self.assertEqual(joined["status"], "CONDITIONAL")
        self.assertLess(joined["scenarios"][0]["geometric"]["MAIN"], 0.10)
