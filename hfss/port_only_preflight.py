"""Solve a disposable 12-mode port-only copy before full 3-D validation.

The source AEDT project is copied, never modified. A successful 2-D port
solve can establish modal Gamma and inspectable port fields, but cannot
provide horn S parameters or far-field validation.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
import traceback
from pathlib import Path

from build_and_solve import solver_messages
from license_environment import restore_ansys_environment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_project", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    source = args.source_project.resolve()
    output = args.output_dir.resolve()
    if not source.is_file():
        parser.error("Source project does not exist")
    if output.exists():
        parser.error("Output directory already exists; refusing to overwrite")
    output.mkdir(parents=True)
    staging = Path(os.environ.get("TEMP", str(output))) / "waveguide_farfield_hfss"
    staging.mkdir(parents=True, exist_ok=True)
    project = staging / f"port_only_12mode_{os.getpid()}_{int(time.time())}.aedt"
    shutil.copy2(source, project)
    receipt = {
        "status": "RUNNING", "source_project": str(source),
        "disposable_project": str(project), "port_modes": 12,
        "full_3d_solve_requested": False, "fields_requested": True,
    }
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        setup_name = "PortOnly30GHz"
        app.odesign.GetModule("AnalysisSetup").InsertSetup("HfssDriven", [
            "NAME:" + setup_name, "Frequency:=", "30GHz",
            "PortsOnly:=", True, "SaveAnyFields:=", True, "IsEnabled:=", True,
        ])
        messages, valid = app.validate_full_design(output_dir=str(staging), ports=12)
        receipt["design_valid"] = bool(valid)
        receipt["validation_messages"] = [str(item) for item in messages]
        if not valid:
            raise RuntimeError("Port-only design validation failed")
        if not app.save_project(str(project)):
            raise RuntimeError("Disposable port-only project save failed")
        project_text = project.read_text(encoding="utf-8", errors="replace")
        marker = f"$begin '{setup_name}'"
        section = project_text.split(marker, 1)[1].split(f"$end '{setup_name}'", 1)[0] \
            if marker in project_text else ""
        receipt["native_port_only_persisted"] = "SolveType='PortsOnly'" in section
        if not receipt["native_port_only_persisted"]:
            raise RuntimeError("AEDT did not persist SolveType='PortsOnly'; refusing analysis")
        setup = app.get_setup(setup_name)
        receipt["analyze_returned"] = bool(app.analyze_setup(setup_name))
        receipt["solver_messages"] = solver_messages(app)
        try:
            receipt["setup_is_solved"] = bool(setup.is_solved)
        except Exception as exc:
            receipt["setup_is_solved"] = False
            receipt["setup_is_solved_error"] = f"{type(exc).__name__}: {exc}"
        receipt["available_sweeps"] = list(app.existing_analysis_sweeps)
        result_dir = project.with_suffix(".aedtresults")
        receipt["result_file_count"] = sum(1 for item in result_dir.rglob("*")
                                            if item.is_file()) if result_dir.is_dir() else 0
        try:
            data = app.post.get_solution_data(
                expressions="Gamma(WavePort1:1)",
                setup_sweep_name=setup_name + " : LastAdaptive",
                report_category="Modal Solution Data",
            )
            receipt["gamma_mode1_samples"] = len(data.primary_sweep_values) if data else 0
            if data:
                receipt["gamma_mode1_real"] = list(data.data_real(
                    "Gamma(WavePort1:1)"))[:3]
                receipt["gamma_mode1_imag"] = list(data.data_imag(
                    "Gamma(WavePort1:1)"))[:3]
        except Exception as exc:
            receipt["gamma_query_error"] = f"{type(exc).__name__}: {exc}"
        engine_failed = any("Engine terminated unexpectedly" in message
                            for message in receipt["solver_messages"])
        if engine_failed:
            receipt["status"] = "PORT_ONLY_SOLVER_ENGINE_FAILED"
        elif receipt.get("gamma_mode1_samples", 0):
            receipt["status"] = "PORT_ONLY_SOLVED"
        else:
            receipt["status"] = "PORT_ONLY_RESULT_NOT_READABLE"
        return 0 if receipt["status"] == "PORT_ONLY_SOLVED" else 2
    except Exception as exc:
        receipt["status"] = "PORT_ONLY_FAILED"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["traceback"] = traceback.format_exc()
        return 2
    finally:
        if app and getattr(app, "desktop_class", None):
            try:
                app.release_desktop(close_projects=True, close_desktop=True)
            except Exception:
                pass
        (output / "port_only_receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
