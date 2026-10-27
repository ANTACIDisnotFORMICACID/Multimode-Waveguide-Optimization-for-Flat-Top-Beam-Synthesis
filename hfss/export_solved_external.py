"""Read a recovered HFSS solve from a fresh AEDT process and export native data.

This does not call Analyze or Save. Source changes are confined to the AEDT
session and discarded when the project is closed. Use a separate recovery copy,
not the only surviving solver result, as the input project.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

import export_solved_in_gui as native_exporter
from export_solved_in_gui import (
    FIELD_EXPRESSIONS,
    FREQUENCY,
    SETUP,
    SPHERE,
    export_complex_cuts,
    export_embedded_patterns,
    export_s_matrix,
    solution_variation,
)
from license_environment import restore_ansys_environment


def write_receipt(path: Path, receipt: dict) -> None:
    temporary = path.with_suffix(".json.partial")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--port-modes", type=int, choices=(10, 12), default=10)
    args = parser.parse_args()
    project = args.project.resolve()
    if not project.is_file():
        parser.error("HFSS project file does not exist")
    output = (args.output_dir or Path(os.environ.get("TEMP", r"C:\Temp")) /
              "waveguide_farfield_hfss" /
              ("external_export_" + time.strftime("%Y%m%dT%H%M%S"))).resolve()
    if output.exists():
        parser.error("Output directory already exists; refusing to overwrite it")
    output.mkdir(parents=True)
    receipt_path = output / "export_receipt.json"
    receipt = {"status": "RUNNING", "project": str(project), "output": str(output),
               "analysis_called_by_script": False, "project_saved_by_script": False,
               "probe_only": args.probe_only, "port_modes": args.port_modes}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        setup = app.setups[0]
        receipt["setup_is_solved"] = bool(setup.is_solved)
        receipt["available_sweeps"] = list(app.existing_analysis_sweeps)
        # Setup.is_solved can disagree with readable post-processing data for
        # recovered projects. The actual S/field queries below are decisive.
        if SETUP not in receipt["available_sweeps"]:
            raise RuntimeError("Setup30GHz : LastAdaptive is not listed")
        try:
            receipt["modal_quantities"] = list(app.post.available_report_quantities(
                report_category="Modal Solution Data", display_type="Data Table",
                solution=SETUP))
        except Exception as exc:
            receipt["modal_quantities_error"] = repr(exc)
        try:
            receipt["far_field_quantities"] = list(app.post.available_report_quantities(
                report_category="Far Fields", display_type="Data Table",
                solution=SETUP, context=SPHERE))
        except Exception as exc:
            receipt["far_field_quantities_error"] = repr(exc)
        try:
            high_level = app.post.get_solution_data(
                expressions=["dB(S(WavePort1:1,WavePort1:1))"],
                setup_sweep_name=SETUP, report_category="Modal Solution Data")
            receipt["high_level_s11_samples"] = len(high_level.primary_sweep_values) if high_level else 0
            if high_level:
                receipt["high_level_s11_data"] = list(high_level.data_real(
                    "dB(S(WavePort1:1,WavePort1:1))"))[:3]
        except Exception as exc:
            receipt["high_level_s11_error"] = repr(exc)
        receipt["setup_is_solved_after_report_queries"] = bool(setup.is_solved)
        native_exporter.PORT_MODES = args.port_modes
        report = app.odesign.GetModule("ReportSetup")
        scalar = "S(WavePort1:1,WavePort1:1)"
        s_sample = solution_variation(report, "Modal Solution Data", [],
                                      ["Freq:=", [FREQUENCY]], [scalar])
        receipt["s11_real"] = list(s_sample.GetRealDataValues(scalar, False))
        receipt["s11_imag"] = list(s_sample.GetImagDataValues(scalar, False))
        field_sample = solution_variation(
            report, "Far Fields", ["Context:=", SPHERE],
            ["Freq:=", [FREQUENCY], "Theta:=", ["All"], "Phi:=", ["0deg"]],
            FIELD_EXPRESSIONS,
        )
        receipt["theta_samples_phi0"] = len(list(field_sample.GetSweepValues("Theta", False)))
        receipt["field_sample_real"] = list(
            field_sample.GetRealDataValues(FIELD_EXPRESSIONS[0], False))[:3]
        receipt["solved_data_checked"] = True
        if args.probe_only:
            receipt["status"] = "PROBE_READABLE"
            return 0
        receipt["s_matrix_csv"] = export_s_matrix(report, str(output))
        cut_path, sample_count = export_complex_cuts(
            report, app.odesign.GetModule("Solutions"), str(output))
        receipt["complex_cuts_csv"] = cut_path
        receipt["complex_cut_samples"] = sample_count
        try:
            receipt["eep_mapping"] = export_embedded_patterns(app.odesign, str(output))
        except Exception as exc:
            receipt["eep_error"] = repr(exc)
        receipt["status"] = "EXPORTED_UNVERIFIED"
        return 0
    except Exception as exc:
        receipt["status"] = "FAILED"
        receipt["error"] = repr(exc)
        receipt["traceback"] = traceback.format_exc()
        return 2
    finally:
        write_receipt(receipt_path, receipt)
        print("HFSS external export receipt: " + str(receipt_path))
        if app is not None:
            try:
                app.release_desktop(close_projects=True, close_desktop=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
