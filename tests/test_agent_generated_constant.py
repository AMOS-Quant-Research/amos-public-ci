import unittest

from agent_result import ANSWER


class AgentGeneratedConstantTest(unittest.TestCase):
    def test_answer_is_seven(self):
        self.assertEqual(ANSWER, 7)


if __name__ == "__main__":
    unittest.main()
