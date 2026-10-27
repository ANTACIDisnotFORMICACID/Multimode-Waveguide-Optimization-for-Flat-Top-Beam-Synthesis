"""Increase the adaptive-pass cap on a COPY of the solved power-check project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from license_environment import restore_ansys_environment


SETUP = "PowerCheck30GHz"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--maximum-passes", type=int, default=18)
    args = parser.parse_args()
    project = args.project.resolve()
    if not project.is_file() or not Path(str(project) + "results").is_dir():
        parser.error("A copied solved project and its results are required")
    if args.receipt.exists() or args.maximum_passes <= 12:
        parser.error("A fresh receipt and a maximum above 12 passes are required")
    receipt = {"project": str(project), "setup": SETUP,
               "new_maximum_passes": args.maximum_passes,
               "analysis_called": False, "status": "RUNNING"}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        sweep = f"{SETUP} : LastAdaptive"
        receipt["had_readable_solution_before_edit"] = sweep in app.existing_analysis_sweeps
        if not receipt["had_readable_solution_before_edit"]:
            raise RuntimeError(f"Existing {sweep} solution not available")
        setup = next((item for item in app.setups if item.name == SETUP), None)
        if setup is None or int(setup.props["MaximumPasses"]) != 12:
            raise RuntimeError("Expected original PowerCheck30GHz with 12 passes")
        if not setup.update({"MaximumPasses": args.maximum_passes}):
            raise RuntimeError("AEDT rejected adaptive-pass cap update")
        if not app.save_project(str(project)):
            raise RuntimeError("Could not save continuation project")
        receipt["readable_solution_after_edit"] = sweep in app.existing_analysis_sweeps
        receipt["status"] = "CONTINUATION_PROJECT_PREPARED"
        return 0
    except Exception as exc:
        receipt.update({"status": "FAILED", "error": repr(exc)})
        raise
    finally:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n",
                                encoding="utf-8")
        if app is not None:
            app.release_desktop(close_projects=True, close_desktop=True)


if __name__ == "__main__":
    raise SystemExit(main())
