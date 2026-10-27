"""Small numerical checks for normalized HFSS/ideal-horn comparison."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compare_candidate_port_mode import compare


class CompareCandidatePortModeTests(unittest.TestCase):
    def test_identical_patterns_have_zero_error(self):
        angles = list(range(-30, 31))
        values = [{"theta": float(angle), "power": math.exp(-(angle / 12) ** 2)}
                  for angle in angles]
        metrics, traces = compare({"E": values, "H": values},
                                  {"E": values, "H": values})
        self.assertEqual(len(metrics), 2)
        self.assertEqual(len(traces), 122)
        for metric in metrics:
            self.assertEqual(metric["PeakDifferenceDeg"], 0)
            self.assertAlmostEqual(metric["HpbwRelativeDifference"], 0)
            self.assertAlmostEqual(metric["PatternRmseDbAboveMinus20"], 0)

    def test_mismatched_angle_grid_is_rejected(self):
        reference = [{"theta": float(angle), "power": 1.0}
                     for angle in range(-3, 4)]
        shifted = [{"theta": item["theta"] + 0.5, "power": item["power"]}
                   for item in reference]
        with self.assertRaisesRegex(ValueError, "grids differ"):
            compare({"E": reference, "H": reference},
                    {"E": shifted, "H": shifted})


if __name__ == "__main__":
    unittest.main()
