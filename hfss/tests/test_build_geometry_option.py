"""Check that a staged geometry CSV does not silently reuse the main result."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_and_solve import read_selected_geometry


class BuildGeometryOptionTests(unittest.TestCase):
    def test_explicit_selection_takes_precedence(self):
        with tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parents[1])) as directory:
            root = Path(directory)
            selection = root / "staged.csv"
            with selection.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "ApertureWidthMm", "ApertureHeightMm", "FlareLengthMm"
                ])
                writer.writeheader()
                writer.writerow({"ApertureWidthMm": 60, "ApertureHeightMm": 20,
                                 "FlareLengthMm": 60})

            geometry = read_selected_geometry(root, selection)
            self.assertEqual(geometry["aperture_width_mm"], 60)
            self.assertEqual(geometry["aperture_height_mm"], 20)
            self.assertEqual(geometry["flare_length_mm"], 60)
            self.assertEqual(geometry["feed_straight_length_mm"], 40)


if __name__ == "__main__":
    unittest.main()
