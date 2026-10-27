"""Offline contract tests for the AEDT in-process exporter."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_solved_in_gui as exporter

TEST_TEMP_ROOT = Path(__file__).resolve().parents[1]


class FakeVariation:
    def GetSweepValues(self, sweep, si_value):
        return [30.0] if sweep == "Freq" else [0.0, 45.0, 90.0]

    def GetSweepUnits(self, sweep):
        return "GHz" if sweep == "Freq" else "deg"

    def GetRealDataValues(self, expression, si_value):
        return [0.1] if expression.startswith("S(") else [1.0, 0.5, 0.1]

    def GetImagDataValues(self, expression, si_value):
        return [0.01]


class FakeReport:
    def __init__(self, solved=True):
        self.solved = solved
        self.calls = []

    def GetSolutionDataPerVariation(self, *args):
        self.calls.append(args)
        return [FakeVariation()] if self.solved else []


class FakeSolutions:
    def __init__(self):
        self.calls = []

    def EditSources(self, settings):
        self.calls.append(settings)


class GuiExporterTests(unittest.TestCase):
    def test_s_matrix_requires_readable_solution(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as folder:
            with self.assertRaises(RuntimeError):
                exporter.export_s_matrix(FakeReport(solved=False), folder)
            self.assertFalse((Path(folder) / "s_matrix_30ghz.csv").exists())

    def test_s_matrix_has_all_100_complex_entries(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as folder:
            path = exporter.export_s_matrix(FakeReport(), folder)
            with open(path, newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 100)
            self.assertEqual({int(row["ReceivePortMode"]) for row in rows}, set(range(1, 11)))
            self.assertEqual({int(row["SourcePortMode"]) for row in rows}, set(range(1, 11)))

    def test_raw_cuts_keep_mode_and_phi_axes(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TEMP_ROOT)) as folder:
            report, solutions = FakeReport(), FakeSolutions()
            path, samples = exporter.export_complex_cuts(report, solutions, folder)
            with open(path, newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(samples, 10 * 4 * 3)
            self.assertEqual(len(rows), samples)
            self.assertEqual({int(row["PhiDeg"]) for row in rows}, {0, 90, 180, 270})
            self.assertEqual(len(solutions.calls), 10)
            for index, settings in enumerate(solutions.calls, start=1):
                self.assertEqual(sum(item[3] == "1W" for item in settings[1:]), 1)
                self.assertEqual(settings[index][1], "WavePort1:" + str(index))


if __name__ == "__main__":
    unittest.main()
