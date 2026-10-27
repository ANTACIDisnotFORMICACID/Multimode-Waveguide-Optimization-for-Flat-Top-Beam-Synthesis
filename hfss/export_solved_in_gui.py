# -*- coding: utf-8 -*-
"""Export a solved waveguide project from Tools > Run Script inside AEDT.

This script never calls Analyze or Save. EditSources only changes the live GUI
session; close the exported copy without saving after the export finishes.
"""

from __future__ import print_function

import csv
import json
import math
import os
import sys
import time
import traceback


DESIGN = "OpenEndedWaveguide"
PROJECT_PREFIX = "waveguide_30ghz"
SETUP = "Setup30GHz : LastAdaptive"
SPHERE = "OpenApertureSphere"
FREQUENCY = "30GHz"
PORT = "WavePort1"
PORT_MODES = 10
INCLUDE_PORT_POST_PROCESSING = True
PHI_DEGREES = (0, 90, 180, 270)
FIELD_EXPRESSIONS = (
    "re(rETheta)", "im(rETheta)", "re(rEPhi)", "im(rEPhi)"
)


def desktop_object():
    try:
        return oDesktop
    except NameError:
        import ScriptEnv
        ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
        return oDesktop


def atomic_json(path, payload):
    temporary = path + ".partial"
    with open(temporary, "w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.rename(temporary, path)


def csv_stream(path):
    # AEDT can run scripts under either IronPython 2 or CPython 3.
    if sys.version_info[0] < 3:
        return open(path, "wb")
    return open(path, "w", newline="")


def solution_variation(report_module, category, context, families, expressions,
                       setup=None):
    if setup is None:
        setup = SETUP
    raw = report_module.GetSolutionDataPerVariation(
        category, setup, context, families, list(expressions)
    )
    variations = list(raw)
    if len(variations) != 1:
        raise RuntimeError("Expected one nominal variation, got " + str(len(variations)))
    return variations[0]


def finite_values(values, label):
    result = [float(value) for value in values]
    if not result or any(math.isnan(value) or math.isinf(value) for value in result):
        raise RuntimeError("Empty or non-finite data: " + label)
    return result


def export_s_matrix(report_module, output):
    expressions = ["S({0}:{1},{0}:{2})".format(PORT, receive, source)
                   for source in range(1, PORT_MODES + 1)
                   for receive in range(1, PORT_MODES + 1)]
    result = solution_variation(
        report_module, "Modal Solution Data", [],
        ["Freq:=", [FREQUENCY]], expressions
    )
    frequencies = finite_values(result.GetSweepValues("Freq", False), "S frequency")
    if len(frequencies) != 1:
        raise RuntimeError("Expected one 30 GHz S-matrix sample")
    path = os.path.join(output, "s_matrix_30ghz.csv")
    with csv_stream(path) as stream:
        writer = csv.writer(stream)
        writer.writerow(["ReceivePortMode", "SourcePortMode", "FreqValue", "FreqUnit",
                         "SReal", "SImag"])
        for source in range(1, PORT_MODES + 1):
            for receive in range(1, PORT_MODES + 1):
                expression = "S({0}:{1},{0}:{2})".format(PORT, receive, source)
                real = finite_values(result.GetRealDataValues(expression, False), expression)
                imag = finite_values(result.GetImagDataValues(expression, False), expression)
                if len(real) != 1 or len(imag) != 1:
                    raise RuntimeError("Unexpected S-matrix trace length: " + expression)
                writer.writerow([receive, source, frequencies[0],
                                 str(result.GetSweepUnits("Freq")), real[0], imag[0]])
    return path


def select_single_mode(solution_module, index):
    settings = [["IncludePortPostProcessing:=", INCLUDE_PORT_POST_PROCESSING,
                 "SpecifySystemPower:=", False]]
    for mode in range(1, PORT_MODES + 1):
        settings.append(["Name:=", "{0}:{1}".format(PORT, mode),
                         "Magnitude:=", "1W" if mode == index else "0W",
                         "Phase:=", "0deg"])
    solution_module.EditSources(settings)


def export_complex_cuts(report_module, solution_module, output):
    path = os.path.join(output, "hfss_raw_complex_cuts.csv")
    with csv_stream(path) as stream:
        writer = csv.writer(stream)
        writer.writerow(["PortMode", "ThetaDeg", "PhiDeg", "EThetaReal",
                         "EThetaImag", "EPhiReal", "EPhiImag"])
        count = 0
        for mode in range(1, PORT_MODES + 1):
            select_single_mode(solution_module, mode)
            for phi in PHI_DEGREES:
                result = solution_variation(
                    report_module, "Far Fields", ["Context:=", SPHERE],
                    ["Freq:=", [FREQUENCY], "Theta:=", ["All"],
                     "Phi:=", ["{0}deg".format(phi)]], FIELD_EXPRESSIONS
                )
                theta = finite_values(result.GetSweepValues("Theta", False), "theta")
                theta_unit = str(result.GetSweepUnits("Theta")).lower()
                if theta_unit not in ("deg", "degree", "degrees"):
                    raise RuntimeError("Unexpected theta unit: " + theta_unit)
                fields = [finite_values(result.GetRealDataValues(expr, False), expr)
                          for expr in FIELD_EXPRESSIONS]
                if any(len(values) != len(theta) for values in fields):
                    raise RuntimeError("Angular grid and field size differ for mode {0}, phi {1}".format(mode, phi))
                if len(theta) < 3:
                    raise RuntimeError("Too few angular samples for mode {0}, phi {1}".format(mode, phi))
                for sample in zip(theta, *fields):
                    writer.writerow([mode, sample[0], phi] + list(sample[1:]))
                count += len(theta)
    return path, count


def export_embedded_patterns(design, output):
    folder = os.path.join(output, "embedded_patterns")
    os.makedirs(folder)
    design.GetModule("RadField").ExportElementPatternToFile([
        "ExportFileName:=", os.path.join(folder, "eep.ffd"),
        "SetupName:=", SPHERE,
        "IntrinsicVariationKey:=", "Freq='30GHz'",
        "DesignVariationKey:=", design.GetNominalVariation(),
        "SolutionName:=", SETUP,
    ])
    mapping = os.path.join(folder, "eep.txt")
    if not os.path.isfile(mapping) or os.path.getsize(mapping) == 0:
        raise RuntimeError("Embedded-pattern mapping is missing or empty")
    return mapping


def main():
    root = os.path.join(os.environ.get("TEMP", r"C:\Temp"), "waveguide_farfield_hfss")
    if not os.path.isdir(root):
        os.makedirs(root)
    output = os.path.join(root, "gui_export_" + time.strftime("%Y%m%dT%H%M%S"))
    if os.path.exists(output):
        raise RuntimeError("Refusing to overwrite " + output)
    os.makedirs(output)
    receipt = {"status": "RUNNING", "output": output, "solved_data_checked": False,
               "project_saved_by_script": False, "analysis_called_by_script": False,
               "setup": SETUP, "port_modes": PORT_MODES,
               "include_port_post_processing": INCLUDE_PORT_POST_PROCESSING}
    receipt_path = os.path.join(output, "export_receipt.json")
    try:
        desktop = desktop_object()
        project = desktop.GetActiveProject()
        if project is None or not str(project.GetName()).lower().startswith(PROJECT_PREFIX):
            raise RuntimeError("Active project is not a waveguide_30ghz copy")
        design = project.SetActiveDesign(DESIGN)
        if design is None:
            raise RuntimeError("OpenEndedWaveguide design is missing")
        receipt["project"] = str(project.GetName())
        report_module = design.GetModule("ReportSetup")
        s_path = export_s_matrix(report_module, output)
        receipt["solved_data_checked"] = True
        receipt["s_matrix_csv"] = s_path
        field_path, samples = export_complex_cuts(
            report_module, design.GetModule("Solutions"), output
        )
        receipt["complex_cuts_csv"] = field_path
        receipt["complex_cut_samples"] = samples
        try:
            receipt["eep_mapping"] = export_embedded_patterns(design, output)
        except Exception as exc:
            # EEP is supplementary: retain the independently readable S data
            # and complex vector cuts even if this export API is unavailable.
            receipt["eep_error"] = repr(exc)
        receipt["status"] = "EXPORTED_UNVERIFIED"
        return 0
    except Exception as exc:
        receipt["status"] = "FAILED"
        receipt["error"] = repr(exc)
        receipt["traceback"] = traceback.format_exc()
        raise
    finally:
        atomic_json(receipt_path, receipt)
        print("HFSS GUI export receipt: " + receipt_path)


if __name__ == "__main__":
    main()
