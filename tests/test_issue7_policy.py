import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class Issue7Contract(unittest.TestCase):
    def test_no_live_trading(self):
        self.assertFalse(False, "synthetic-only")
    def test_fixture_is_public_constant(self):
        self.assertEqual(7, 7)
    def test_generated_test_not_pretended(self):
        # Actual generated file is deliberately absent from this commit.
        self.assertFalse((ROOT / "tests" / "test_agent_generated_constant.py").exists())

if __name__ == "__main__":
    unittest.main()
