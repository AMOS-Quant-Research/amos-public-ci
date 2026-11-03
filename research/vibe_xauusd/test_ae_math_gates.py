import unittest
from ae_math_gates import dynamic_ddr_scale, dd_velocity_guard, risk_constrained_kelly_moment

class AEMathGateTests(unittest.TestCase):
    def test_ddr_boundaries(self):
        self.assertAlmostEqual(dynamic_ddr_scale(0, 0.2), 1)
        self.assertEqual(dynamic_ddr_scale(0.2, 0.2), 0)
        self.assertEqual(dynamic_ddr_scale(0.3, 0.2), 0)
        self.assertGreater(dynamic_ddr_scale(0.1, 0.2), 0)

    def test_dd_velocity_guard(self):
        self.assertAlmostEqual(dd_velocity_guard(0, 0), 1)
        self.assertLess(dd_velocity_guard(1, 1), 1)
        self.assertAlmostEqual(dd_velocity_guard(-1, -1), 1)

    def test_kelly_moment(self):
        self.assertAlmostEqual(risk_constrained_kelly_moment([1], [1], 2), 1)
        self.assertGreater(risk_constrained_kelly_moment([0.5,0.5], [1.1,0.9], 2), 1)

    def test_bad_parameters(self):
        with self.assertRaises(ValueError): dynamic_ddr_scale(0,0)
        with self.assertRaises(ValueError): dd_velocity_guard(float("nan"),0)
        with self.assertRaises(ValueError): risk_constrained_kelly_moment([1],[0],1)

if __name__ == "__main__":
    unittest.main()
