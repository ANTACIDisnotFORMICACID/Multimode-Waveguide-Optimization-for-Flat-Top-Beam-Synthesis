# -*- coding: utf-8 -*-
"""Export 15-pass S matrices under both AEDT port post-processing settings.

Run inside the saved project via Tools > Run Script. No Analyze or Save is used.
The two tables establish whether the S report depends on this GUI setting.
"""

from __future__ import print_function

import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_solved_in_gui as exporter


def main():
    exporter.oDesktop = oDesktop
    exporter.SETUP = "PowerCheck30GHz : LastAdaptive"
    exporter.PORT_MODES = 12
    root = os.path.join(os.environ.get("TEMP", r"C:\Temp"), "waveguide_farfield_hfss")
    output = os.path.join(root, "gui_s_reference_15pass_" + time.strftime("%Y%m%dT%H%M%S"))
    os.makedirs(output)
    receipt = {"status": "RUNNING", "setup": exporter.SETUP,
               "analysis_called": False, "project_saved_by_script": False,
               "output": output}
    try:
        project = oDesktop.GetActiveProject()
        if project is None or "power_refine_gui" not in str(project.GetName()):
            raise RuntimeError("Active project is not the power-refinement project")
        design = project.SetActiveDesign("OpenEndedWaveguide")
        solution = design.GetModule("Solutions")
        report = design.GetModule("ReportSetup")
        paths = {}
        for label, setting in (("postprocessed_50ohm", True),
                               ("intrinsic_modal", False)):
            folder = os.path.join(output, label)
            os.makedirs(folder)
            exporter.INCLUDE_PORT_POST_PROCESSING = setting
            exporter.select_single_mode(solution, 1)
            paths[label] = exporter.export_s_matrix(report, folder)
        receipt.update({"status": "TWO_S_REFERENCES_EXPORTED", "s_matrix_csv": paths})
    except Exception as exc:
        receipt.update({"status": "FAILED", "error": repr(exc),
                        "traceback": traceback.format_exc()})
        raise
    finally:
        path = os.path.join(output, "receipt.json")
        with open(path, "w") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
        print("HFSS GUI S-reference receipt: " + path)


if __name__ == "__main__":
    main()
