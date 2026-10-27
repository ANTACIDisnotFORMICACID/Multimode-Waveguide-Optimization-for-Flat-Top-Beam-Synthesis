"""Add an independent PML-mesh/refined adaptive setup to a copied solved horn."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from license_environment import restore_ansys_environment


NEW_SETUP = "PowerCheck30GHz"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path,
                        help="A new COPY of the solved project and .aedtresults")
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    receipt_path = args.receipt.resolve()
    if not project.is_file() or not Path(str(project) + "results").is_dir():
        parser.error("Copied project and matching solved results are both required")
    if receipt_path.exists():
        parser.error("Receipt already exists")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"status": "RUNNING", "project": str(project),
               "analysis_called": False, "new_setup": NEW_SETUP}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        if "Setup30GHz : LastAdaptive" not in app.existing_analysis_sweeps:
            raise RuntimeError("Baseline solved data are not readable")
        if NEW_SETUP in [setup.name for setup in app.setups]:
            raise RuntimeError("Refinement setup already exists")
        pml_objects = sorted(name for name in app.modeler.object_names
                             if name.startswith("PML_RadiatingSurface_"))
        if len(pml_objects) != 26:
            raise RuntimeError(f"Expected 26 PML surface objects, got {len(pml_objects)}")
        mesh = app.mesh.assign_surface_mesh(pml_objects, level=3,
                                            name="PMLSurfaceRefine")
        if not mesh:
            raise RuntimeError("PML surface mesh assignment failed")
        setup = app.create_setup(
            name=NEW_SETUP, setup_type="HFSSDriven",
            Frequency="30GHz", MaxDeltaS=0.005,
            MaximumPasses=12, MinimumPasses=3,
            MinimumConvergedPasses=3)
        if not setup:
            raise RuntimeError("Refinement adaptive setup creation failed")
        messages, valid = app.validate_full_design(
            output_dir=str(project.parent), ports=12)
        receipt["design_validation"] = {"valid": bool(valid),
                                        "messages": [str(m) for m in messages]}
        if not valid:
            raise RuntimeError("Refinement design validation failed")
        if not app.save_project(str(project)):
            raise RuntimeError("Refinement project was not saved")
        receipt.update({"status": "REFINEMENT_PROJECT_PREPARED",
                        "pml_object_count": len(pml_objects),
                        "surface_mesh_level": 3,
                        "max_delta_s": 0.005,
                        "minimum_converged_passes": 3,
                        "maximum_passes": 12,
                        "next_action": "In normal AEDT GUI analyze PowerCheck30GHz only, then save."})
        return 0
    except Exception as exc:
        receipt.update({"status": "FAILED", "error": repr(exc)})
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n",
                                encoding="utf-8")
        if app is not None:
            app.release_desktop(close_projects=True, close_desktop=True)


if __name__ == "__main__":
    raise SystemExit(main())
