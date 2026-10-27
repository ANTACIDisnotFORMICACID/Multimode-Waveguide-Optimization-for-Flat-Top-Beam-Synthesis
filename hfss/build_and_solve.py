"""Build and optionally solve the open-ended rectangular waveguide in HFSS.

The script writes a mode-count-specific status file. A missing
license, API incompatibility, or incomplete solve is reported as BLOCKED;
no substitute data are written under an HFSS label.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

from license_environment import restore_ansys_environment


AEDT_VERSION = "2025.2"
AEDT_ROOT = Path(r"D:\Program Files\ANSYS Inc\v252\AnsysEM")
FREQUENCY = "30GHz"
SETUP = "Setup30GHz"
SPHERE = "OpenApertureSphere"
PORT = "WavePort1"
PORT_MODES = 12


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def solver_messages(app) -> list[str]:
    """Read AEDT's desktop messages without persisting license-server names."""
    messages = []
    for project, design in (("", ""), (app.project_name, "")):
        try:
            messages.extend(app.odesktop.GetMessages(project, design, 0))
        except Exception as exc:
            messages.append(f"AEDT message query failed: {type(exc).__name__}")
    filtered = []
    for message in messages:
        line = str(message)
        if any(term in line.lower() for term in ("error", "fail", "license", "warning")):
            line = re.sub(r"\b\d+@[-\w.]+\b", "[license-server]", line)
            filtered.append(line)
    return list(dict.fromkeys(filtered))[-30:]


def read_selected_geometry(root: Path, selection_csv: Path | None = None) -> dict[str, float]:
    path = selection_csv if selection_csv is not None else root / "results" / "tables" / "selected_geometry.csv"
    if not path.is_file():
        raise RuntimeError("selected_geometry.csv is missing; run the MATLAB geometry scan first")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        row = next(csv.DictReader(stream))
    return {
        "aperture_width_mm": float(row["ApertureWidthMm"]),
        "aperture_height_mm": float(row["ApertureHeightMm"]),
        "flare_length_mm": float(row["FlareLengthMm"]),
        "feed_straight_length_mm": 40.0,
    }


def far_field_complex_cut(app, phi_deg: int) -> tuple[list[float], list[complex], list[complex]]:
    variations = {"Freq": [FREQUENCY], "Theta": ["All"], "Phi": [f"{phi_deg}deg"]}
    data = app.post.get_solution_data(
        expressions=["rETheta", "rEPhi"],
        setup_sweep_name=f"{SETUP} : LastAdaptive",
        variations=variations,
        primary_sweep_variable="Theta",
        report_category="Far Fields",
        context=SPHERE,
    )
    if not data:
        raise RuntimeError(f"HFSS returned no far-field data for phi={phi_deg} deg")
    theta = [float(value) for value in data.primary_sweep_values]
    e_theta = [complex(real, imag) for real, imag in zip(
        data.data_real("rETheta"), data.data_imag("rETheta")
    )]
    e_phi = [complex(real, imag) for real, imag in zip(
        data.data_real("rEPhi"), data.data_imag("rEPhi")
    )]
    return theta, e_theta, e_phi


def signed_complex_cut(app, positive_phi: int, negative_phi: int):
    theta_pos, et_pos, ep_pos = far_field_complex_cut(app, positive_phi)
    theta_neg, et_neg, ep_neg = far_field_complex_cut(app, negative_phi)
    # At a negative signed angle the phi+180 spherical transverse basis
    # points opposite to the basis used on the positive cut.
    negative = [(-theta, -et, -ep) for theta, et, ep in zip(theta_neg, et_neg, ep_neg) if theta > 0]
    return sorted(negative + list(zip(theta_pos, et_pos, ep_pos)), key=lambda item: item[0])


def export_excitation_patterns(app, output_dir: Path, port_modes: int) -> Path:
    rows: list[dict] = []
    excitations = list(app.excitations)
    for mode_index in range(1, port_modes + 1):
        source = f"{PORT}:{mode_index}"
        source_settings = {name: ("0W", "0deg") for name in excitations}
        source_settings[source] = ("1W", "0deg")
        if not app.edit_sources(source_settings, include_port_post_processing=True):
            raise RuntimeError(f"Could not activate {source}")
        for plane, positive_phi, negative_phi in (("E", 90, 270), ("H", 0, 180)):
            samples = signed_complex_cut(app, positive_phi, negative_phi)
            for angle, e_theta, e_phi in samples:
                rows.append(
                    {
                        "PortMode": mode_index,
                        "AnalyticMode": "UNIDENTIFIED",
                        "Plane": plane,
                        "ThetaDeg": angle,
                        "EThetaReal": e_theta.real,
                        "EThetaImag": e_theta.imag,
                        "EPhiReal": e_phi.real,
                        "EPhiImag": e_phi.imag,
                        "ModeCorrelation": math.nan,
                        "IdentificationStatus": "PENDING_PORT_FIELD_CORRELATION",
                    }
                )
    path = output_dir / f"hfss_port_mode_patterns_{port_modes}mode.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def horn_sheet(app, points, name: str):
    sheet = app.modeler.create_polyline(
        points,
        name=name,
        cover_surface=True,
        close_surface=True,
    )
    if not sheet:
        raise RuntimeError(f"Could not create horn wall {name}")
    return sheet


def build_model(app, geometry: dict[str, float], port_modes: int = PORT_MODES):
    from ansys.aedt.core.generic.constants import Plane

    app.modeler.model_units = "mm"
    aperture_width = geometry["aperture_width_mm"]
    aperture_height = geometry["aperture_height_mm"]
    flare_length = geometry["flare_length_mm"]
    feed_length = geometry["feed_straight_length_mm"]
    throat_z = -flare_length
    port_z = throat_z - feed_length
    # Four-corner sheets avoid orientation-dependent rectangle dimensions.
    straight_walls = [
        horn_sheet(app, [[-10, -5, port_z], [-10, 5, port_z],
                         [-10, 5, throat_z], [-10, -5, throat_z]], "FeedXMinus"),
        horn_sheet(app, [[10, -5, port_z], [10, 5, port_z],
                         [10, 5, throat_z], [10, -5, throat_z]], "FeedXPlus"),
        horn_sheet(app, [[-10, -5, port_z], [10, -5, port_z],
                         [10, -5, throat_z], [-10, -5, throat_z]], "FeedYMinus"),
        horn_sheet(app, [[-10, 5, port_z], [10, 5, port_z],
                         [10, 5, throat_z], [-10, 5, throat_z]], "FeedYPlus"),
    ]
    horn_walls = [
        horn_sheet(app, [[-10, -5, throat_z], [-aperture_width / 2, -aperture_height / 2, 0],
                         [-aperture_width / 2, aperture_height / 2, 0], [-10, 5, throat_z]], "HornXMinus"),
        horn_sheet(app, [[10, -5, throat_z], [aperture_width / 2, -aperture_height / 2, 0],
                         [aperture_width / 2, aperture_height / 2, 0], [10, 5, throat_z]], "HornXPlus"),
        horn_sheet(app, [[-10, -5, throat_z], [10, -5, throat_z],
                         [aperture_width / 2, -aperture_height / 2, 0], [-aperture_width / 2, -aperture_height / 2, 0]], "HornYMinus"),
        horn_sheet(app, [[-10, 5, throat_z], [10, 5, throat_z],
                         [aperture_width / 2, aperture_height / 2, 0], [-aperture_width / 2, aperture_height / 2, 0]], "HornYPlus"),
    ]
    walls = straight_walls + horn_walls
    port_sheet = app.modeler.create_rectangle(
        Plane.XY, [-10, -5, port_z], [20, 10], name="WavePortSheet"
    )
    # The PML region makes this port internal; a PEC backing removes the
    # air-filled half-space behind it, leaving propagation toward +Z.
    port_backing = app.modeler.create_box(
        [-10, -5, port_z - 1], [20, 10, 1],
        name="WavePortPecBacking", material="pec"
    )
    if not all(walls) or not port_sheet or not port_backing:
        raise RuntimeError("HFSS geometry creation failed")
    boundary = app.assign_perfecte_to_sheets([wall.name for wall in walls], name="PEC_Waveguide")
    if not boundary:
        raise RuntimeError("PEC boundary assignment failed")
    wave_port = app.wave_port(
        port_sheet,
        modes=port_modes,
        # TE10 has E_y at x=0. The former horizontal centerline had zero
        # E·dl and AEDT warned that mode-1 polarity was undefined.
        integration_line=[[0, -5, port_z], [0, 5, port_z]],
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
    parser.add_argument("--selected-geometry-csv", type=Path,
                        help="Use an explicitly staged MATLAB geometry result without changing repository tables")
    parser.add_argument("--solve", action="store_true")
    parser.add_argument("--graphical", action="store_true", help="Launch the AEDT user interface")
    parser.add_argument("--port-modes", type=int, choices=(10, 12), default=12,
                        help="10 reproduces the legacy solve; 12 includes both near-cutoff modes")
    args = parser.parse_args()
    root = args.project_root.resolve()
    output_dir = root / "results" / "hfss"
    project_dir = root / "hfss" / "projects"
    output_dir.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.port_modes == 10 else "_12mode"
    status_path = output_dir / f"hfss_status{suffix}.json"
    repository_project_path = project_dir / f"waveguide_30ghz{suffix}.aedt"
    staging_dir = Path(os.environ.get("TEMP", str(project_dir))) / "waveguide_farfield_hfss"
    staging_dir.mkdir(parents=True, exist_ok=True)
    # Always start from a fresh project.  Re-opening a previous empty or
    # partially written AEDT file can leave PyAEDT with a project handle but
    # no design object, which is indistinguishable from a launch failure.
    project_path = staging_dir / f"waveguide_30ghz{suffix}_2025r2_{os.getpid()}.aedt"
    status = {
        "status": "BLOCKED",
        "stage": "preflight",
        "aedt_version": AEDT_VERSION,
        "pyaedt_version": None,
        "project": str(project_path),
        "repository_project": str(repository_project_path),
        "solve_requested": args.solve,
        "port_modes": args.port_modes,
        "license_verified": False,
        "message": "HFSS workflow has not started.",
    }
    write_json(status_path, status)
    app = None
    started = time.time()
    try:
        # Automation shells may omit existing machine/user Ansys settings.
        # Record only where settings were found, never their values.
        status["restored_environment_sources"] = restore_ansys_environment()
        # Keep the release discovery explicit for the local AEDT installation.
        if AEDT_ROOT.is_dir():
            os.environ.setdefault("ANSYSEM_ROOT252", str(AEDT_ROOT))
        import ansys.aedt.core as pyaedt
        from ansys.aedt.core import Hfss
        from ansys.aedt.core.application import design_solutions

        # AEDT 2025 R2's HFSS Scripting Guide specifies DrivenModal as the
        # InsertDesign solution identifier (not the PyAEDT display label).
        design_solutions.solutions_defaults["HFSS"] = "DrivenModal"

        geometry = read_selected_geometry(root, args.selected_geometry_csv)
        status["geometry"] = geometry
        status["pyaedt_version"] = getattr(pyaedt, "__version__", "unknown")
        status["stage"] = "launch"
        status["message"] = "Launching AEDT and creating an HFSS design; license checkout is not yet verified."
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
        status["stage"] = "model"
        setup = build_model(app, geometry, args.port_modes)
        validation_messages, design_valid = app.validate_full_design(
            output_dir=str(staging_dir), ports=args.port_modes
        )
        status["design_validation"] = {
            "valid": bool(design_valid),
            "messages": [str(message) for message in validation_messages],
        }
        if not design_valid:
            raise RuntimeError("HFSS design validation did not pass")
        if not app.save_project(str(project_path)):
            raise RuntimeError("HFSS project save failed")
        shutil.copy2(project_path, repository_project_path)
        status["status"] = "MODEL_BUILT"
        status["message"] = (
            f"Selected pyramidal horn, fixed {args.port_modes}-mode feed port, PML, setup, and far-field sphere were created."
        )
        write_json(status_path, status)
        if not args.solve:
            return 0

        status["stage"] = "solve"
        status["status"] = "RUNNING"
        status["message"] = "Adaptive HFSS solve is running."
        write_json(status_path, status)
        solved = app.analyze_setup(SETUP)
        status["analyze_setup_returned"] = bool(solved)
        status["solver_messages"] = solver_messages(app)
        try:
            status["solution_available"] = bool(setup.is_solved)
        except Exception as exc:
            status["solution_available"] = False
            status["solution_check_error"] = type(exc).__name__
        write_json(status_path, status)
        if not status["solution_available"]:
            raise RuntimeError("HFSS produced no readable adaptive solution")
        status["license_verified"] = True
        mesh_path = output_dir / f"mesh_statistics_{args.port_modes}mode.csv"
        staging_mesh_path = staging_dir / f"mesh_statistics_{os.getpid()}.csv"
        if app.export_mesh_stats(SETUP, output_file=str(staging_mesh_path)):
            shutil.copy2(staging_mesh_path, mesh_path)
        status["stage"] = "export"
        export_excitation_patterns(app, output_dir, args.port_modes)
        if not app.save_project(str(project_path)):
            raise RuntimeError("HFSS project save after solve failed")
        shutil.copy2(project_path, repository_project_path)
        status["status"] = "SOLVED_UNIDENTIFIED_MODES"
        status["message"] = (
            f"HFSS solved and exported complex Etheta/Ephi for all {args.port_modes} feed-port modes. "
            "Analytical TE/TM labels remain pending until port-field correlation exceeds 0.95."
        )
        return 0
    except Exception as exc:  # the status file is the durable failure report
        status["status"] = "BLOCKED"
        if status["stage"] == "solve" and any(
            "Engine terminated unexpectedly" in line for line in status.get("solver_messages", [])
        ):
            status["status"] = "BLOCKED_SOLVER_ENGINE_CRASH"
            status["message"] = (
                "HFSSCOMENGINE terminated unexpectedly; no readable adaptive solution was produced."
            )
        elif status["stage"] == "launch" and "should return None" in str(exc):
            status["message"] = (
                "AEDT 2025 R2 launched, but its API returned no HFSS design object. "
                "The solver license was not verified; check AEDT design creation "
                "and licensing settings before retrying."
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
