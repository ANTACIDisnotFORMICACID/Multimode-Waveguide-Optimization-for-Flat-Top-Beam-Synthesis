"""Try a lower-memory HFSS matrix solver on the single 12-pass working copy.

Run only after archiving the direct-solver 12-pass project with results. This
script edits and saves the working project but does not call Analyze.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from license_environment import restore_ansys_environment


SETUP = "PowerCheck30GHz"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    project, archive = args.project.resolve(), args.archive.resolve()
    if not project.is_file() or not Path(str(project) + "results").is_dir():
        parser.error("Saved working project and matching results are required")
    if not archive.is_file() or archive.stat().st_size < 1_000_000:
        parser.error("A verified archive of the direct-solver solution is required")
    if args.receipt.exists() or Path(str(project) + ".lock").exists():
        parser.error("Receipt exists or the working project is open")
    receipt = {"status": "RUNNING", "project": str(project),
               "preserved_archive": str(archive), "setup": SETUP,
               "analysis_called": False}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        sweep = f"{SETUP} : LastAdaptive"
        if sweep not in app.existing_analysis_sweeps:
            raise RuntimeError("The archived 12-pass checkpoint is not readable in the working copy")
        setup = next((item for item in app.setups if item.name == SETUP), None)
        if setup is None:
            raise RuntimeError(f"Missing setup {SETUP}")
        before = {key: setup.props[key] for key in
                  ("DrivenSolverType", "MaximumPasses", "MaxDeltaS", "MinimumConvergedPasses")}
        if (str(before["DrivenSolverType"]) != "Direct Solver" or
                int(before["MaximumPasses"]) != 12 or
                float(before["MaxDeltaS"]) != 0.005 or
                int(before["MinimumConvergedPasses"]) != 3):
            raise RuntimeError(f"Unexpected starting setup: {before}")
        if not setup.update({"DrivenSolverType": "Iterative Solver",
                             "IterativeResidual": 1e-6,
                             "MaximumPasses": 15}):
            raise RuntimeError("AEDT rejected the iterative solver settings")
        if not app.save_project(str(project)):
            raise RuntimeError("Iterative trial project could not be saved")
        receipt.update({"status": "ITERATIVE_TRIAL_PREPARED",
                        "previous_settings": before,
                        "new_settings": {key: setup.props.get(key) for key in
                                         ("DrivenSolverType", "IterativeResidual",
                                          "MaximumPasses", "MaxDeltaS",
                                          "MinimumConvergedPasses")},
                        "prior_solution_still_readable": sweep in app.existing_analysis_sweeps})
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
