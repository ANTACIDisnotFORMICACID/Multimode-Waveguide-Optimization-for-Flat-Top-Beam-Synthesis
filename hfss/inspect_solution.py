"""Read-only inspection of a saved HFSS project's solution availability."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from license_environment import restore_ansys_environment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--design", default="OpenEndedWaveguide")
    parser.add_argument("--setup", default="Setup30GHz")
    parser.add_argument("--solution", default="LastAdaptive")
    parser.add_argument("--port", default="WavePort1:1")
    args = parser.parse_args()
    restore_ansys_environment()
    from ansys.aedt.core import Hfss

    app = None
    try:
        app = Hfss(project=str(args.project.resolve()), design=args.design,
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        setup = f"{args.setup} : {args.solution}"
        report = {
            "project": str(args.project.resolve()),
            "design": app.design_name,
            "setups": [item.name for item in app.setups],
            "available_sweeps": list(app.existing_analysis_sweeps),
        }
        try:
            report["modal_report_solutions"] = list(app.post.available_report_solutions(
                report_category="Modal Solution Data"))
        except Exception as exc:
            report["modal_report_solutions_error"] = type(exc).__name__
        try:
            report["modal_categories"] = list(app.post.available_quantities_categories(
                report_category="Modal Solution Data", display_type="Data Table",
                solution=setup))
        except Exception as exc:
            report["modal_categories_error"] = type(exc).__name__
        try:
            report["far_field_quantities"] = list(app.post.available_report_quantities(
                report_category="Far Fields", display_type="Data Table",
                solution=setup, context="OpenApertureSphere"))
        except Exception as exc:
            report["far_field_quantities_error"] = type(exc).__name__
        try:
            selected_setup = next(item for item in app.setups if item.name == args.setup)
            report["setup_is_solved"] = bool(selected_setup.is_solved)
        except Exception as exc:
            report["setup_is_solved_error"] = type(exc).__name__
        try:
            expression = (f"Gamma({args.port})" if args.setup == "PortOnly30GHz"
                          else f"dB(S({args.port},{args.port}))")
            modal = app.post.get_solution_data(
                expressions=[expression],
                setup_sweep_name=setup, report_category="Modal Solution Data")
            report["modal_data_samples"] = len(modal.primary_sweep_values) if modal else 0
        except Exception as exc:
            report["modal_data_error"] = type(exc).__name__
        print(json.dumps(report, indent=2))
        return 0
    finally:
        if app is not None:
            app.release_desktop(close_projects=True, close_desktop=True)


if __name__ == "__main__":
    raise SystemExit(main())
