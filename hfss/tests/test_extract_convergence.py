"""Offline adaptive-convergence parser checks."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract_convergence import parse_convergence


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1]


def example(current):
    values = []
    for pass_number, elements, delta in ((1, 1000, None), (2, 1300, 0.04),
                                         (3, 1800, 0.006), (4, 2300, 0.001)):
        lines = ["$begin 'QuantityValues'", f"PassNo={pass_number}",
                 "Intrinsics='Freq=\\'30000000000\\''", f"SolvedElements({elements}, 0)"]
        if delta is not None:
            lines.append(f"MaxMagDeltaS({delta}, 0)")
        lines.append("$end 'QuantityValues'")
        values.extend(lines)
    return ("IsConverged=true\nMaxPasses='15'\nConvTarget='0.02'\n"
            "ConvTargetConsecPasses='3'\nConvCurrentConsecPasses='" + str(current) + "'\n"
            + "\n".join(values))


class ExtractConvergenceTests(unittest.TestCase):
    def test_three_consecutive_passes_required(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as name:
            path = Path(name) / "sample.EMConvData"
            path.write_text(example(2), encoding="utf-8")
            parsed = parse_convergence(path)
            self.assertEqual(len(parsed["passes"]), 4)
            self.assertFalse(parsed["target_reached_for_required_passes"])
            path.write_text(example(3), encoding="utf-8")
            self.assertTrue(parse_convergence(path)["target_reached_for_required_passes"])


if __name__ == "__main__":
    unittest.main()
