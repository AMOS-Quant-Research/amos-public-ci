import tempfile
import unittest
from pathlib import Path
from public_ci_receipt import make_receipt


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.log = Path(self.temp.name) / "test.log"
        self.log.write_text("Ran 9 tests in 0.003s\n\nOK\n", encoding="utf-8")

    def test_success_never_implies_private_validation(self):
        r = make_receipt(self.log, commit="a" * 40, run_id="123", exit_code=0)
        self.assertEqual(r["scope"], "PUBLIC_SYNTHETIC_ONLY")
        self.assertFalse(r["private_source_tested"])
        self.assertFalse(r["nautilus_raw_tick_verified"])
        self.assertFalse(r["execution_allowed"])

    def test_failure_never_issues_receipt(self):
        with self.assertRaises(ValueError):
            make_receipt(self.log, commit="a" * 40, run_id="123", exit_code=1)

    def test_missing_pass_summary_rejected(self):
        self.log.write_text("Ran 9 tests\nFAILED (failures=1)\n")
        with self.assertRaises(ValueError):
            make_receipt(self.log, commit="a" * 40, run_id="123", exit_code=0)


if __name__ == "__main__":
    unittest.main()
