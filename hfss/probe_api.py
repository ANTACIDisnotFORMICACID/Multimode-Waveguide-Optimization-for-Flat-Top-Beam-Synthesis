"""Probe AEDT design creation before running the full electromagnetic model."""

import argparse
import json
import os
from pathlib import Path

from license_environment import restore_ansys_environment

RESTORED_ENVIRONMENT = restore_ansys_environment()
os.environ.setdefault("ANSYSEM_ROOT252", r"D:\Program Files\ANSYS Inc\v252\AnsysEM")

from ansys.aedt.core import Hfss
import ansys.aedt.core as pyaedt
from ansys.aedt.core.application import design_solutions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--graphical", action="store_true")
    parser.add_argument("--solution-type", choices=["Modal", "Terminal"], default="Modal")
    parser.add_argument("--driven-modal-insert", action="store_true",
                        help="Use AEDT scripting's DrivenModal design identifier")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    project_path = output_dir / "api_probe.aedt"
    app = None
    receipt = {"pyaedt": pyaedt.__version__, "project": str(project_path),
               "graphical": args.graphical, "solution_type_requested": args.solution_type,
               "driven_modal_insert": args.driven_modal_insert,
               "restored_environment_sources": RESTORED_ENVIRONMENT}
    try:
        if args.driven_modal_insert:
            design_solutions.solutions_defaults["HFSS"] = "DrivenModal"
        app = Hfss(project=str(project_path), design="ApiProbe", solution_type=args.solution_type,
                   version="2025.2", non_graphical=not args.graphical, new_desktop=True,
                   close_on_exit=True)
        receipt.update(design_name=app.design_name, solution_type=app.solution_type)
        assert app.design_name == "ApiProbe"
        saved = app.save_project()
        receipt["project_saved"] = bool(saved) and project_path.is_file()
        assert receipt["project_saved"]
        receipt["status"] = "DESIGN_CREATED"
    except Exception as exc:
        receipt.update(status="FAILED", error=f"{type(exc).__name__}: {exc}")
    finally:
        (output_dir / "api_probe.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        if app:
            app.release_desktop(close_projects=True, close_desktop=True)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "DESIGN_CREATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
