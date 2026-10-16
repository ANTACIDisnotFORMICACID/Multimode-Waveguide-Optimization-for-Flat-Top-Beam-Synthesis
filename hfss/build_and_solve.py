"""Build and optionally solve the open-ended rectangular waveguide in HFSS.

The script always writes ``results/hfss/hfss_status.json``. A missing
license, API incompatibility, or incomplete solve is reported as BLOCKED;
no substitute data are written under an HFSS label.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import sys
import time
import traceback
from pathlib import Path


AEDT_VERSION = "2025.2"
AEDT_ROOT = Path(r"D:\Program Files\ANSYS Inc\v252\AnsysEM")
FREQUENCY = "30GHz"
SETUP = "Setup30GHz"
SPHERE = "OpenApertureSphere"
PORT = "WavePort1"
PORT_MODES = 10


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def far_field_cut(app, phi_deg: int) -> tuple[list[float], list[float]]:
    variations = {"Freq": [FREQUENCY], "Theta": ["All"], "Phi": [f"{phi_deg}deg"]}
    data = app.post.get_solution_data(
        expressions="dB(GainTotal)",
        setup_sweep_name=f"{SETUP} : LastAdaptive",
        variations=variations,
        primary_sweep_variable="Theta",
        report_category="Far Fields",
        context=SPHERE,
    )
    if not data:
        raise RuntimeError(f"HFSS returned no far-field data for phi={phi_deg} deg")
    theta = [float(value) for value in data.primary_sweep_values]
    gain = [float(value) for value in data.data_real("dB(GainTotal)")]
    return theta, gain


def signed_cut(app, positive_phi: int, negative_phi: int) -> tuple[list[float], list[float]]:
    theta_pos, gain_pos = far_field_cut(app, positive_phi)
    theta_neg, gain_neg = far_field_cut(app, negative_phi)
    negative = [(-theta, gain) for theta, gain in zip(theta_neg, gain_neg) if theta > 0]
    combined = sorted(negative + list(zip(theta_pos, gain_pos)), key=lambda item: item[0])
    peak = max(value for _, value in combined)
    return [item[0] for item in combined], [item[1] - peak for item in combined]


def export_excitation_patterns(app, output_dir: Path) -> Path:
    rows: list[dict] = []
    excitations = list(app.excitations)
    for mode_index in range(1, PORT_MODES + 1):
        source = f"{PORT}:{mode_index}"
        source_settings = {name: ("0W", "0deg") for name in excitations}
        source_settings[source] = ("1W", "0deg")
        if not app.edit_sources(source_settings, include_port_post_processing=True):
            raise RuntimeError(f"Could not activate {source}")
        for plane, positive_phi, negative_phi in (("E", 0, 180), ("H", 90, 270)):
            theta, gain = signed_cut(app, positive_phi, negative_phi)
            for angle, value in zip(theta, gain):
                rows.append(
                    {
                        "PortMode": mode_index,
                        "AnalyticMode": "UNIDENTIFIED",
                        "Plane": plane,
                        "ThetaDeg": angle,
                        "GainDb": value,
                    }
                )
    path = output_dir / "hfss_port_mode_patterns.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def build_model(app):
    app.modeler.model_units = "mm"
    walls = [
        app.modeler.create_rectangle(app.PLANE.YZ, [-10, -5, -80], [10, 80], name="WallXMinus"),
        app.modeler.create_rectangle(app.PLANE.YZ, [10, -5, -80], [10, 80], name="WallXPlus"),
        app.modeler.create_rectangle(app.PLANE.XZ, [-10, -5, -80], [20, 80], name="WallYMinus"),
        app.modeler.create_rectangle(app.PLANE.XZ, [-10, 5, -80], [20, 80], name="WallYPlus"),
    ]
    port_sheet = app.modeler.create_rectangle(
        app.PLANE.XY, [-10, -5, -80], [20, 10], name="WavePortSheet"
    )
    if not all(walls) or not port_sheet:
        raise RuntimeError("HFSS geometry creation failed")
    boundary = app.assign_perfecte_to_sheets([wall.name for wall in walls], name="PEC_Waveguide")
    if not boundary:
        raise RuntimeError("PEC boundary assignment failed")
    wave_port = app.wave_port(
        port_sheet,
        modes=PORT_MODES,
        integration_line=[[-10, 0, -80], [10, 0, -80]],
        name=PORT,
        renormalize=True,
    )
    if not wave_port:
        raise RuntimeError("Multimode wave-port assignment failed")
    if not app.create_open_region(frequency=FREQUENCY, boundary="PML"):
        raise RuntimeError("PML open-region creation failed")
    setup = app.create_setup(
        name=SETUP,
        setup_type="HFSSDriven",
        Frequency=FREQUENCY,
        MaxDeltaS=0.02,
        MaximumPasses=15,
        MinimumPasses=3,
        MinimumConvergedPasses=3,
    )
    if not setup:
        raise RuntimeError("Adaptive setup creation failed")
    sphere = app.insert_infinite_sphere(
        definition="Theta-Phi",
        x_start=0,
        x_stop=90,
        x_step=0.5,
        y_start=0,
        y_stop=270,
        y_step=90,
        name=SPHERE,
    )
    if not sphere:
        raise RuntimeError("Infinite-sphere setup failed")
    return setup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--solve", action="store_true")
    parser.add_argument("--graphical", action="store_true", help="Launch the AEDT user interface")
    args = parser.parse_args()
    root = args.project_root.resolve()
    output_dir = root / "results" / "hfss"
    project_dir = root / "hfss" / "projects"
    output_dir.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "hfss_status.json"
    repository_project_path = project_dir / "waveguide_30ghz.aedt"
    staging_dir = Path(os.environ.get("TEMP", str(project_dir))) / "waveguide_farfield_hfss"
    staging_dir.mkdir(parents=True, exist_ok=True)
    project_path = staging_dir / "waveguide_30ghz_2025r2.aedt"
    status = {
        "status": "BLOCKED",
        "stage": "preflight",
        "aedt_version": AEDT_VERSION,
        "pyaedt_version": None,
        "project": str(project_path),
        "repository_project": str(repository_project_path),
        "solve_requested": args.solve,
        "license_verified": False,
        "message": "HFSS workflow has not started.",
    }
    write_json(status_path, status)
    app = None
    started = time.time()
    try:
        # PyAEDT 0.9.x discovers releases through ANSYSEM_ROOTxxx.  Some
        # standalone AEDT installations omit that process environment
        # variable even though the executable is present.
        if AEDT_ROOT.is_dir():
            os.environ.setdefault("ANSYSEM_ROOT252", str(AEDT_ROOT))
        import pyaedt
        from pyaedt import Hfss
        from pyaedt.application import design_solutions

        # PyAEDT 0.9.6 predates AEDT 2025 R2 and otherwise asks a new HFSS
        # project to start as a terminal network before switching it to
        # modal.  Request the intended modal network at insertion time.
        design_solutions.solutions_defaults["HFSS"] = "HFSS Modal Network"

        status["pyaedt_version"] = getattr(pyaedt, "__version__", "unknown")
        status["stage"] = "launch"
        status["message"] = "Launching AEDT and checking out an HFSS license."
        write_json(status_path, status)
        app = Hfss(
            project=str(project_path),
            design="OpenEndedWaveguide",
            solution_type="Modal",
            version=AEDT_VERSION,
            non_graphical=not args.graphical,
            new_desktop=True,
            close_on_exit=True,
            remove_lock=True,
        )
        status["license_verified"] = True
        status["stage"] = "model"
        setup = build_model(app)
        app.save_project(str(project_path))
        shutil.copy2(project_path, repository_project_path)
        status["status"] = "MODEL_BUILT"
        status["message"] = "Geometry, 10-mode wave port, PML, setup, and far-field sphere were created."
        write_json(status_path, status)
        if not args.solve:
            return 0

        status["stage"] = "solve"
        status["status"] = "RUNNING"
        status["message"] = "Adaptive HFSS solve is running."
        write_json(status_path, status)
        solved = app.analyze_setup(SETUP)
        if not solved:
            raise RuntimeError("HFSS analyze_setup returned False")
        mesh_path = output_dir / "mesh_statistics.csv"
        app.export_mesh_stats(SETUP, mesh_path=str(mesh_path))
        status["stage"] = "export"
        export_excitation_patterns(app, output_dir)
        app.save_project(str(project_path))
        shutil.copy2(project_path, repository_project_path)
        status["status"] = "SOLVED_UNIDENTIFIED_MODES"
        status["message"] = (
            "HFSS solved and exported all ten port-mode patterns. Analytical TE/TM labels "
            "must be assigned by the MATLAB comparison before a multimode claim is made."
        )
        return 0
    except Exception as exc:  # the status file is the durable failure report
        status["status"] = "BLOCKED"
        if status["stage"] == "launch" and "should return None" in str(exc):
            status["message"] = (
                "AEDT 2025 R2 launched, but its API returned no HFSS design object. "
                "The solver license was not verified; likely causes are license checkout "
                "failure or PyAEDT 0.9.6/AEDT 2025 R2 API incompatibility."
            )
        else:
            status["message"] = str(exc)
        status["traceback"] = traceback.format_exc()
        return 2
    finally:
        status["elapsed_seconds"] = time.time() - started
        write_json(status_path, status)
        if app and getattr(app, "desktop_class", None):
            try:
                app.release_desktop(close_projects=True, close_desktop=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
