"""Export solved wave-port propagation constants and impedances from HFSS.

Use a fresh disposable copy of the solved AEDT project. This script never
calls Analyze or Save. Report quantity names are discovered at runtime, not
guessed from port numbering.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import traceback
from pathlib import Path

from export_solved_in_gui import FREQUENCY, SETUP, solution_variation
from license_environment import restore_ansys_environment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--port-modes", type=int, choices=(10, 12), default=12)
    parser.add_argument("--port-only", action="store_true",
                        help="Read the native PortOnly30GHz : PortOnly report")
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output_dir.resolve()
    if not project.is_file():
        parser.error("Project does not exist")
    if output.exists():
        parser.error("Output directory already exists")
    output.mkdir(parents=True)
    receipt = {"status": "RUNNING", "project": str(project),
               "port_modes": args.port_modes, "analysis_called": False,
               "project_saved": False, "categories": {}, "quantities": {}}
    setup_sweep = "PortOnly30GHz : PortOnly" if args.port_only else SETUP
    receipt["setup_sweep"] = setup_sweep
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        available = app.post.available_report_solutions(
            report_category="Modal Solution Data")
        if setup_sweep not in available:
            raise RuntimeError(f"Report solution {setup_sweep} is not readable")
        category_names = app.post.available_quantities_categories(
            report_category="Modal Solution Data", display_type="Data Table",
            solution=setup_sweep)
        receipt["categories"] = list(category_names)
        rows = []
        report = app.odesign.GetModule("ReportSetup")
        for label in ("Gamma", "Port Zo"):
            matches = [name for name in category_names if name.casefold() == label.casefold()]
            if len(matches) != 1:
                raise RuntimeError(f"Expected one {label} category, got {matches}")
            quantities = list(app.post.available_report_quantities(
                report_category="Modal Solution Data", display_type="Data Table",
                solution=setup_sweep, quantities_category=matches[0]))
            receipt["quantities"][label] = quantities
            quantity_prefix = "Gamma" if label == "Gamma" else "Zo"
            expected = [f"{quantity_prefix}(WavePort1:{index})"
                        for index in range(1, args.port_modes + 1)]
            if set(expected) != set(quantities):
                raise RuntimeError(f"Unexpected {label} quantity list: {quantities}")
            solved = solution_variation(report, "Modal Solution Data", [],
                                        ["Freq:=", [FREQUENCY]], expected,
                                        setup=setup_sweep)
            for index, expression in enumerate(expected, start=1):
                real = list(solved.GetRealDataValues(expression, False))
                imag = list(solved.GetImagDataValues(expression, False))
                if len(real) != 1 or len(imag) != 1:
                    raise RuntimeError(f"Invalid solved trace for {expression}")
                rows.append({"PortMode": index, "Quantity": label,
                             "Real": float(real[0]), "Imag": float(imag[0]),
                             "Unit": str(solved.GetDataUnits(expression))})
        with (output / "port_modal_data_30ghz.csv").open(
                "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream,
                                    fieldnames=["PortMode", "Quantity", "Real", "Imag", "Unit"])
            writer.writeheader()
            writer.writerows(rows)
        receipt["row_count"] = len(rows)
        receipt["status"] = "EXPORTED_UNVERIFIED"
        return 0
    except Exception as exc:
        receipt["status"] = "FAILED"
        receipt["error"] = repr(exc)
        receipt["traceback"] = traceback.format_exc()
        return 2
    finally:
        (output / "export_receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print("HFSS port modal receipt: " + str(output / "export_receipt.json"))
        if app is not None:
            try:
                app.release_desktop(close_projects=True, close_desktop=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
