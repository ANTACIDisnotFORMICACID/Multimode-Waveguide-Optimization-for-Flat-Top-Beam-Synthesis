"""Synthetic-data checks for the post-GUI-export import gate."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_gui_export import validate_export


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1]


def synthetic_export(folder, *, duplicate=False, incomplete=False, port_modes=10):
    (folder / "export_receipt.json").write_text(json.dumps({
        "status": "EXPORTED_UNVERIFIED", "solved_data_checked": True,
        "analysis_called_by_script": False, "project_saved_by_script": False,
        "complex_cut_samples": port_modes * 4 * 181,
        "port_modes": port_modes,
    }), encoding="utf-8")
    with (folder / "s_matrix_30ghz.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["ReceivePortMode", "SourcePortMode", "FreqValue", "FreqUnit", "SReal", "SImag"])
        for source in range(1, port_modes + 1):
            for receive in range(1, port_modes + 1):
                writer.writerow([receive, source, 30, "GHz", 0.1, 0.01])
    with (folder / "hfss_raw_complex_cuts.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["PortMode", "ThetaDeg", "PhiDeg", "EThetaReal", "EThetaImag", "EPhiReal", "EPhiImag"])
        for mode in range(1, port_modes + 1):
            for phi in (0, 90, 180, 270):
                if incomplete and mode == port_modes and phi == 270:
                    continue
                for step in range(181):
                    writer.writerow([mode, step / 2, phi, 1, 0.2, 0.5, -0.3])
                if duplicate and mode == 1 and phi == 0:
                    writer.writerow([mode, 90, phi, 1, 0.2, 0.5, -0.3])


class ValidateGuiExportTests(unittest.TestCase):
    def test_accepts_complete_complex_port_mode_grid_and_reverses_basis(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as name:
            folder = Path(name)
            synthetic_export(folder)
            summary, signed = validate_export(folder)
            self.assertEqual(summary["status"], "RAW_EXPORT_VALIDATED")
            self.assertEqual(summary["s_matrix_entries"], 100)
            self.assertEqual(summary["raw_complex_samples"], 7240)
            self.assertEqual(len(signed), 10 * 2 * 361)
            self.assertEqual(signed[0]["Plane"], "E")
            self.assertEqual(signed[0]["ThetaDeg"], -90)
            self.assertEqual(signed[0]["EThetaReal"], -1)
            self.assertEqual(signed[0]["EPhiImag"], 0.3)
            self.assertEqual(signed[180]["ThetaDeg"], 0)
            self.assertEqual(signed[180]["EThetaReal"], 1)

    def test_rejects_duplicate_angle(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as name:
            folder = Path(name)
            synthetic_export(folder, duplicate=True)
            with self.assertRaisesRegex(ValueError, "Unsorted, duplicated"):
                validate_export(folder)

    def test_rejects_missing_mode_cut(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as name:
            folder = Path(name)
            synthetic_export(folder, incomplete=True)
            with self.assertRaisesRegex(ValueError, "Expected 40"):
                validate_export(folder)

    def test_accepts_native_external_receipt_with_direct_solution_samples(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as name:
            folder = Path(name)
            synthetic_export(folder)
            receipt_path = folder / "export_receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            del receipt["solved_data_checked"]
            receipt.update({"setup_is_solved": True, "theta_samples_phi0": 181,
                            "s11_real": [0.5], "s11_imag": [0.0]})
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            summary, _ = validate_export(folder)
            self.assertEqual(summary["s_matrix_entries"], 100)

    def test_accepts_twelve_mode_export(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as name:
            folder = Path(name)
            synthetic_export(folder, port_modes=12)
            summary, signed = validate_export(folder)
            self.assertEqual(summary["s_matrix_entries"], 144)
            self.assertEqual(summary["port_mode_count"], 12)
            self.assertEqual(len(signed), 12 * 2 * 361)


if __name__ == "__main__":
    unittest.main()
