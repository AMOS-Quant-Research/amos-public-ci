import unittest

from agent_result import ANSWER


class TestAgentGeneratedConstant(unittest.TestCase):
    def test_answer(self):
        self.assertEqual(ANSWER, 7)


if __name__ == "__main__":
    unittest.main()
