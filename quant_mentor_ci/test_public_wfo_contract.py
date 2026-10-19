import unittest
from public_wfo_contract import walk_forward, public_result_envelope


def rows(pnl):
    return [{"timestamp": f"2026-01-{i+1:02d}T00:00:00Z", "net_pnl": v}
            for i, v in enumerate(pnl)]


class WFOPublicContract(unittest.TestCase):
    def test_train_only_choice_is_not_future_peeking(self):
        data = {"a": rows([5, 5, 5, 5, -8, -8, 2, 2]),
                "b": rows([-1, -1, -1, -1, 10, 10, 3, 3])}
        result = walk_forward(data, train_size=4, test_size=2)
        self.assertEqual(result["folds"][0]["parameter"], "a")
        self.assertEqual(result["folds"][0]["oos"]["pnl"], -16)
        self.assertEqual(result["validation"], "SYNTHETIC_CONTRACT_ONLY")
        self.assertFalse(result["execution_allowed"])

    def test_mismatched_timestamp_rejected(self):
        a = rows([1] * 8)
        b = rows([2] * 8)
        b[3]["timestamp"] = "2026-03-31T00:00:00Z"
        with self.assertRaises(ValueError):
            walk_forward({"a": a, "b": b}, train_size=4, test_size=2)

    def test_no_synthetic_to_verified_escalation(self):
        data = {"a": rows([1] * 8), "b": rows([2] * 8)}
        result = walk_forward(data, train_size=4, test_size=2)
        envelope = public_result_envelope(result, source_commit="a" * 40)
        self.assertFalse(envelope["engine_verified"])
        self.assertEqual(len(envelope["result_sha256"]), 64)

    def test_invalid_commit_rejected(self):
        data = {"a": rows([1] * 8), "b": rows([2] * 8)}
        with self.assertRaises(ValueError):
            public_result_envelope(walk_forward(data, train_size=4, test_size=2),
                                   source_commit="not-a-sha")


if __name__ == "__main__":
    unittest.main()
