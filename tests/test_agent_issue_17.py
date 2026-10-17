import unittest

from agent_result import ANSWER

class Issue17AgentResult(unittest.TestCase):
    def test_answer_is_17(self):
        self.assertEqual(ANSWER, 17)

if __name__ == "__main__":
    unittest.main()
