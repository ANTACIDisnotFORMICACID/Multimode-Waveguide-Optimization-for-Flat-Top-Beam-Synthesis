"""Minimal one-port HFSS solve to separate installation faults from horn faults."""

from __future__ import annotations

import json
import os
from pathlib import Path

from license_environment import restore_ansys_environment


def main() -> int:
    restored = restore_ansys_environment()
    from ansys.aedt.core import Hfss
    from ansys.aedt.core.application import design_solutions

    design_solutions.solutions_defaults["HFSS"] = "DrivenModal"
    project = (Path(os.environ["TEMP"]) / "waveguide_farfield_hfss"
               / f"one_mode_solver_smoke_{os.getpid()}.aedt")
    project.parent.mkdir(parents=True, exist_ok=True)
    app = None
    report = {"project": str(project), "restored_environment_sources": restored}
    try:
        app = Hfss(project=str(project), design="OneModeGuide", solution_type="Modal",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        app.modeler.model_units = "mm"
        guide = app.modeler.create_box([-10, -5, 0], [20, 10, 20],
                                       name="GuideAir", material="vacuum")
        if not guide:
            raise RuntimeError("Could not create guide air volume")
        port_face = next((face for face in guide.faces
                          if abs(app.modeler.get_face_center(face.id)[2]) < 1e-8), None)
        if port_face is None:
            raise RuntimeError("Could not identify input face")
        if not app.wave_port(port_face, modes=1, name="InputPort"):
            raise RuntimeError("Could not assign wave port")
        setup = app.create_setup(name="Smoke30GHz", setup_type="HFSSDriven",
                                 Frequency="30GHz", MaxDeltaS=0.1,
                                 MaximumPasses=3, MinimumPasses=1)
        messages, valid = app.validate_full_design(output_dir=str(project.parent), ports=1)
        report["design_valid"] = bool(valid)
        report["validation_messages"] = [str(item) for item in messages]
        if not valid:
            raise RuntimeError("Minimal guide failed design validation")
        if not app.save_project(str(project)):
            raise RuntimeError("Minimal guide save failed")
        report["analyze_returned"] = bool(app.analyze_setup("Smoke30GHz", cores=1))
        try:
            report["solution_available"] = bool(setup.is_solved)
        except Exception as exc:
            report["solution_available"] = False
            report["solution_check_error"] = type(exc).__name__
        if not report["solution_available"]:
            raise RuntimeError("Minimal guide produced no readable solution")
        report["status"] = "SOLVED"
        return 0
    except Exception as exc:
        report["status"] = "FAILED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        return 2
    finally:
        output = Path(__file__).resolve().parents[1] / "results" / "hfss" / "solver_smoke.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if app:
            app.release_desktop(close_projects=True, close_desktop=True)
        print(json.dumps({key: value for key, value in report.items()
                          if key != "validation_messages"}, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
