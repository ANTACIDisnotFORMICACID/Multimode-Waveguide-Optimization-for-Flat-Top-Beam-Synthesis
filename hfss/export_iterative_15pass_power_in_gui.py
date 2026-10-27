# -*- coding: utf-8 -*-
"""Read intrinsic antenna power for two fixed excitations inside AEDT GUI.

Open the saved 15-pass project and use Tools > Run Script. This script does
not analyze or save the project. Its output is an English-path temporary CSV.
"""

from __future__ import print_function

import csv
import json
import math
import os
import sys
import time
import traceback


SETUP = "PowerCheck30GHz : LastAdaptive"
SPHERE = "OpenApertureSphere"
QUANTITIES = ("IncidentPower", "AcceptedPower", "RadiatedPower",
              "RadiationEfficiency", "PeakRealizedGain")


def desktop_object():
    try:
        return oDesktop
    except NameError:
        import ScriptEnv
        ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
        return oDesktop


def read_weights():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(project_root, "results", "hfss",
                        "twelve_mode_60x20x60_three_mode_2d_intrinsic_20261027",
                        "selected_weights.csv")
    weights = {}
    with open(path, "r") as stream:
        for row in csv.DictReader(stream):
            mode = int(row["PortMode"])
            if mode in weights or not 1 <= mode <= 12:
                raise ValueError("Invalid or duplicate port mode")
            weights[mode] = (float(row["Amplitude"]), float(row["PhaseDeg"]))
    if abs(sum(amplitude ** 2 for amplitude, _ in weights.values()) - 1) > 1e-8:
        raise ValueError("Three-mode weights are not normalized to 1 W")
    return path, weights


def edit_sources(solution, weights):
    settings = [["IncludePortPostProcessing:=", False,
                 "SpecifySystemPower:=", False]]
    for mode in range(1, 13):
        amplitude, phase = weights.get(mode, (0.0, 0.0))
        settings.append(["Name:=", "WavePort1:{0}".format(mode),
                         "Magnitude:=", "{0:.15g}W".format(amplitude ** 2),
                         "Phase:=", "{0:.15g}deg".format(phase)])
    solution.EditSources(settings)


def csv_stream(path):
    if sys.version_info[0] < 3:
        return open(path, "wb")
    return open(path, "w", newline="")


def main():
    root = os.path.join(os.environ.get("TEMP", r"C:\Temp"), "waveguide_farfield_hfss")
    if not os.path.isdir(root):
        os.makedirs(root)
    output = os.path.join(root, "gui_power_15pass_" + time.strftime("%Y%m%dT%H%M%S"))
    os.makedirs(output)
    receipt = {"status": "RUNNING", "output": output, "setup": SETUP,
               "analysis_called": False, "project_saved_by_script": False,
               "include_port_post_processing": False}
    try:
        project = desktop_object().GetActiveProject()
        if project is None or "power_refine_gui" not in str(project.GetName()):
            raise RuntimeError("Active project is not the power-refinement work project")
        design = project.SetActiveDesign("OpenEndedWaveguide")
        solution = design.GetModule("Solutions")
        report = design.GetModule("ReportSetup")
        weight_path, three_mode = read_weights()
        receipt["weights_csv"] = weight_path
        cases = (("port 1", {1: (1.0, 0.0)}),
                 ("ports 1+5+8 2D intrinsic optimized", three_mode))
        rows = []
        for name, weights in cases:
            edit_sources(solution, weights)
            data = list(report.GetSolutionDataPerVariation(
                "Antenna Parameters", SETUP, ["Context:=", SPHERE],
                ["Freq:=", ["30GHz"]], list(QUANTITIES)))
            if len(data) != 1:
                raise RuntimeError("Expected one antenna-parameter variation for " + name)
            row = {"case": name, "include_port_post_processing": False}
            for quantity in QUANTITIES:
                values = list(data[0].GetRealDataValues(quantity, False))
                if (len(values) != 1 or math.isnan(float(values[0])) or
                        math.isinf(float(values[0]))):
                    raise RuntimeError("Missing or invalid " + quantity + " for " + name)
                row[quantity] = float(values[0])
            rows.append(row)
        path = os.path.join(output, "native_power_comparison.csv")
        with csv_stream(path) as stream:
            writer = csv.DictWriter(stream, fieldnames=["case", "include_port_post_processing"]
                                    + list(QUANTITIES))
            writer.writeheader()
            writer.writerows(rows)
        receipt.update({"status": "POWER_EXPORTED", "csv": path, "row_count": len(rows)})
    except Exception as exc:
        receipt.update({"status": "FAILED", "error": repr(exc),
                        "traceback": traceback.format_exc()})
        raise
    finally:
        path = os.path.join(output, "receipt.json")
        with open(path, "w") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
        print("HFSS GUI power receipt: " + path)


if __name__ == "__main__":
    main()
