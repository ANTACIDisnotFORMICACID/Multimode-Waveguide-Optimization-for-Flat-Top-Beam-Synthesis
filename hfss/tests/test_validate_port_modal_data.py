"""Offline checks for HFSS propagation-constant group comparison."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_port_modal_data import validate


class PortModalDataTests(unittest.TestCase):
    def test_degenerate_group_remains_ambiguous(self):
        with tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parents[1])) as temporary:
            root = Path(temporary)
            metadata = root / "metadata"
            metadata.mkdir()
            (metadata / "export_receipt.json").write_text(json.dumps({
                "status": "EXPORTED_UNVERIFIED", "port_modes": 2,
                "analysis_called": False, "project_saved": False,
            }), encoding="utf-8")
            with (metadata / "port_modal_data_30ghz.csv").open(
                    "w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["PortMode", "Quantity", "Real", "Imag", "Unit"])
                writer.writerows([
                    [1, "Gamma", 0, 22.9, ""], [2, "Gamma", 0, 23.1, ""],
                    [1, "Port Zo", 50, 0, ""], [2, "Port Zo", 50, 0, ""],
                ])
            catalog = root / "catalog.csv"
            with catalog.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Name", "Status", "betaRadPerM"])
                writer.writerows([["TE02", "propagating", 23],
                                  ["TE40", "propagating", 23]])
            output = root / "checked"
            summary = validate(metadata, catalog, output)
            self.assertEqual(summary["near_cutoff_port_modes"], [2, 1])
            with (output / "modal_dispersion_comparison.csv").open(
                    newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["CandidateModesByBeta"], "TE02|TE40")
            self.assertEqual(rows[1]["CandidateModesByBeta"], "TE02|TE40")


if __name__ == "__main__":
    unittest.main()
