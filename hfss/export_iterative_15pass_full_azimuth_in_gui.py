# -*- coding: utf-8 -*-
"""Export a 15-pass 12-mode full-azimuth embedded field inside AEDT GUI.

Uses the AEDT 2025 R2 documented RadField.InsertInfiniteSphereSetup and
ExportElementPatternToFile APIs. No Analyze or Save is performed. Source
amplitudes use the intrinsic modal reference, matching the 12-pass basis.
"""

from __future__ import print_function

import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_solved_in_gui as exporter


SETUP = "PowerCheck30GHz : LastAdaptive"


def main():
    exporter.oDesktop = oDesktop
    exporter.PORT_MODES = 12
    exporter.INCLUDE_PORT_POST_PROCESSING = False
    root = os.path.join(os.environ.get("TEMP", r"C:\Temp"), "waveguide_farfield_hfss")
    stamp = time.strftime("%Y%m%dT%H%M%S")
    output = os.path.join(root, "gui_full_azimuth_15pass_" + stamp)
    sphere = "FullAzimuth15_" + stamp
    os.makedirs(output)
    receipt = {"status": "RUNNING", "output": output, "setup": SETUP,
               "sphere": sphere, "analysis_called": False,
               "project_saved_by_script": False,
               "include_port_post_processing": False}
    try:
        project = oDesktop.GetActiveProject()
        if project is None or "power_refine_gui" not in str(project.GetName()):
            raise RuntimeError("Active project is not the 15-pass power-refinement project")
        design = project.SetActiveDesign("OpenEndedWaveguide")
        if design is None:
            raise RuntimeError("OpenEndedWaveguide design is missing")
        solution = design.GetModule("Solutions")
        radiation = design.GetModule("RadField")
        exporter.select_single_mode(solution, 1)
        radiation.InsertInfiniteSphereSetup([
            "NAME:" + sphere,
            "UseCustomRadiationSurface:=", False,
            "CSDefinition:=", "Theta-Phi",
            "Polarization:=", "Linear",
            "ThetaStart:=", "0deg", "ThetaStop:=", "90deg", "ThetaStep:=", "0.5deg",
            "PhiStart:=", "0deg", "PhiStop:=", "355deg", "PhiStep:=", "5deg",
            "UseLocalCS:=", False,
        ])
        pattern = os.path.join(output, "eep.ffd")
        radiation.ExportElementPatternToFile([
            "ExportFileName:=", pattern,
            "SetupName:=", sphere,
            "IntrinsicVariationKey:=", "Freq='30GHz'",
            "DesignVariationKey:=", design.GetNominalVariation(),
            "SolutionName:=", SETUP,
        ])
        mapping = os.path.join(output, "eep.txt")
        if not os.path.isfile(mapping):
            raise RuntimeError("Embedded-pattern mapping was not written")
        modes = {}
        with open(mapping, "r") as stream:
            for line in stream:
                parts = line.split()
                if parts and parts[0].startswith("WavePort1:"):
                    mode = int(parts[0].split(":", 1)[1])
                    path = os.path.join(output, parts[1] + ".ffd")
                    if mode in modes or not os.path.isfile(path) or os.path.getsize(path) < 10000:
                        raise RuntimeError("Missing or duplicated FFD for port mode " + str(mode))
                    modes[mode] = path
        if set(modes) != set(range(1, 13)):
            raise RuntimeError("Expected 12 embedded modal FFD files")
        receipt.update({"status": "FULL_AZIMUTH_FFD_EXPORTED_UNVERIFIED",
                        "mode_count": 12, "theta_samples_expected": 181,
                        "phi_samples_expected": 72, "mapping": mapping,
                        "ffd_files": modes})
    except Exception as exc:
        receipt.update({"status": "FAILED", "error": repr(exc),
                        "traceback": traceback.format_exc()})
        raise
    finally:
        path = os.path.join(output, "receipt.json")
        with open(path, "w") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
        print("HFSS GUI full-azimuth receipt: " + path)


if __name__ == "__main__":
    main()
