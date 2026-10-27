"""Offline checks for analytic comparison of sampled transverse E fields."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_port_plane_proxy import normalized_correlation, transverse_template


class PortPlaneProxyTests(unittest.TestCase):
    def setUp(self):
        x, y = np.meshgrid(np.linspace(-9, 9, 19), np.linspace(-4.5, 4.5, 19))
        self.x, self.y = x.ravel(), y.ravel()

    def test_te10_has_y_field_only_and_phase_invariant_match(self):
        te10 = transverse_template("TE", 1, 0, self.x, self.y)
        count = len(self.x)
        self.assertTrue(np.allclose(te10[:count], 0))
        self.assertGreater(np.linalg.norm(te10[count:]), 0)
        self.assertAlmostEqual(normalized_correlation(te10, 1j * te10), 1.0)

    def test_distinct_spatial_patterns_do_not_alias(self):
        te10 = transverse_template("TE", 1, 0, self.x, self.y)
        te20 = transverse_template("TE", 2, 0, self.x, self.y)
        self.assertLess(normalized_correlation(te10, te20), 1e-12)

    def test_te_tm_template_family_differs(self):
        te = transverse_template("TE", 1, 1, self.x, self.y)
        tm = transverse_template("TM", 1, 1, self.x, self.y)
        self.assertLess(normalized_correlation(te, tm), 0.1)


if __name__ == "__main__":
    unittest.main()
