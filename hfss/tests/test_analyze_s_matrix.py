"""Offline checks for native complex S-matrix diagnostics."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_s_matrix import diagnostics


class SMatrixDiagnosticsTests(unittest.TestCase):
    def test_reciprocal_passive_example(self):
        matrix = np.array([[0.1, 0.2j], [0.2j, -0.3]], dtype=complex)
        summary, rows = diagnostics(matrix)
        self.assertAlmostEqual(summary["max_reciprocity_error"], 0)
        self.assertLess(summary["max_singular_value"], 1)
        self.assertAlmostEqual(rows[0]["SelfReflectionMagnitude"], 0.1)


if __name__ == "__main__":
    unittest.main()
