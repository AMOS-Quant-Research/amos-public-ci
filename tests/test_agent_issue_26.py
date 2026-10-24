import unittest

from agent_result import ANSWER


class AgentIssue26Tests(unittest.TestCase):
    def test_answer(self):
        self.assertEqual(ANSWER, 26)


if __name__ == "__main__":
    unittest.main()
