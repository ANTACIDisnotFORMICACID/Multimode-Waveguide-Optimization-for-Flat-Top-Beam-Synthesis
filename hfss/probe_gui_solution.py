# -*- coding: utf-8 -*-
"""Read-only AEDT GUI probe for a saved HFSS adaptive solution.

Run with Tools > Run Script in the project that should contain the solution.
No analysis, source editing, project save, or result deletion is performed.
"""

from __future__ import print_function

import json
import os
import time
import traceback


SETUP = "Setup30GHz : LastAdaptive"


def attempt(probe, name, operation):
    try:
        value = operation()
        probe[name] = {"ok": True, "value": value}
    except Exception as exc:
        probe[name] = {"ok": False, "error": repr(exc),
                       "traceback": traceback.format_exc()}


def single_trace(report, expression, family):
    values = list(report.GetSolutionDataPerVariation(
        "Modal Solution Data", SETUP, [], ["Freq:=", [family]], [expression]
    ))
    if not values:
        return {"variation_count": 0}
    data = values[0]
    return {"variation_count": len(values),
            "frequencies": list(data.GetSweepValues("Freq", False)),
            "real": list(data.GetRealDataValues(expression, False)),
            "imag": list(data.GetImagDataValues(expression, False))}


def main():
    try:
        desktop = oDesktop
    except NameError:
        import ScriptEnv
        ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
        desktop = oDesktop
    project = desktop.GetActiveProject()
    if project is None:
        raise RuntimeError("No active project")
    design = project.SetActiveDesign("OpenEndedWaveguide")
    if design is None:
        raise RuntimeError("OpenEndedWaveguide design missing")
    report = design.GetModule("ReportSetup")
    solutions = design.GetModule("Solutions")
    probe = {"project": str(project.GetName()), "design": str(design.GetName()),
             "setup": SETUP, "read_only": True}
    attempt(probe, "solved_variations", lambda: list(solutions.ListVariations(SETUP)))
    for label, expression in (("indexed", "S(WavePort1:1,WavePort1:1)"),
                              ("plain", "S(WavePort1,WavePort1)")):
        for family in ("All", "30GHz"):
            attempt(probe, "trace_" + label + "_" + family,
                    lambda expression=expression, family=family:
                    single_trace(report, expression, family))
    root = os.path.join(os.environ.get("TEMP", r"C:\Temp"), "waveguide_farfield_hfss")
    if not os.path.isdir(root):
        os.makedirs(root)
    path = os.path.join(root, "gui_solution_probe_" +
                        time.strftime("%Y%m%dT%H%M%S") + ".json")
    with open(path, "w") as stream:
        json.dump(probe, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("HFSS GUI solution probe: " + path)


if __name__ == "__main__":
    main()
