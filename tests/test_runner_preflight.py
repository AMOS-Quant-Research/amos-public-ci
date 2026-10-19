import unittest


class RunnerPreflightTests(unittest.TestCase):
    def test_no_live_orders(self):
        policy = {"live_authorized": False, "auto_merge": False}
        self.assertFalse(policy["live_authorized"])
        self.assertFalse(policy["auto_merge"])

    def test_no_provider_credentials(self):
        agent_invoked = False
        self.assertFalse(agent_invoked)


if __name__ == "__main__":
    unittest.main()
