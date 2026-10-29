import unittest
import numpy as np
from ae_original_kelly import kelly_grid_solve

class KellyOriginalTests(unittest.TestCase):
    def test_strict_risk_moment(self):
        outcomes=np.array([0.12]*75+[-0.08]*25,dtype=float)
        f=kelly_grid_solve(outcomes,lam=2,n_grid=101)
        self.assertGreater(f,0)
        self.assertLessEqual(np.mean(np.power(1+f*outcomes,-2)),1+1e-10)
        self.assertGreater(np.mean(np.log(1+f*outcomes)),0)

    def test_no_edge_flat(self):
        self.assertEqual(kelly_grid_solve([-0.01]*80),0.0)

    def test_bankruptcy_infeasible(self):
        self.assertEqual(kelly_grid_solve([-2.0]*80),0.0)

    def test_bad_input_flat(self):
        self.assertEqual(kelly_grid_solve([0.1]*5),0.0)

if __name__ == "__main__": unittest.main()
