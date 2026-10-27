"""Create a separate AEDT GUI project with an explicit native Ports Only setup.

Unlike a PyAEDT setup property that can be accepted in memory but omitted
from the saved AEDT project, this script verifies AEDT persisted the native
``SolveType='PortsOnly'`` representation before offering the file for GUI analysis.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from license_environment import restore_ansys_environment


SETUP = "PortOnly30GHz"


def persisted_setup_section(project_text: str, setup_name: str) -> str:
    marker = f"$begin '{setup_name}'"
    if marker not in project_text:
        return ""
    return project_text.split(marker, 1)[1].split(f"$end '{setup_name}'", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve()
    receipt_path = args.receipt.resolve()
    if not source.is_file():
        parser.error("Source project does not exist")
    if destination.exists() or destination.with_suffix(".aedtresults").exists():
        parser.error("Destination project or results already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    receipt = {"source": str(source), "destination": str(destination),
               "setup": SETUP, "status": "BUILDING", "analysis_called": False}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(destination), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        analysis = app.odesign.GetModule("AnalysisSetup")
        # Keep this disposable port study unambiguous in the GUI: Analyze All
        # must have only the native two-dimensional port setup available.
        analysis.DeleteSetups(["Setup30GHz"])
        analysis.InsertSetup("HfssDriven", [
            "NAME:" + SETUP,
            "Frequency:=", "30GHz",
            "PortsOnly:=", True,
            "SaveAnyFields:=", True,
            "IsEnabled:=", True,
        ])
        messages, valid = app.validate_full_design(output_dir=str(destination.parent), ports=12)
        receipt["design_valid"] = bool(valid)
        receipt["validation_messages"] = [str(item) for item in messages]
        if not valid:
            raise RuntimeError("12-mode port design validation failed")
        if not app.save_project(str(destination)):
            raise RuntimeError("AEDT project save failed")
        receipt["status"] = "SAVED_UNVERIFIED"
    except Exception as exc:
        receipt["status"] = "BUILD_FAILED"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if app and getattr(app, "desktop_class", None):
            try:
                app.release_desktop(close_projects=True, close_desktop=True)
            except Exception:
                pass

    if receipt["status"] == "SAVED_UNVERIFIED":
        project_text = destination.read_text(encoding="utf-8", errors="replace")
        section = persisted_setup_section(project_text, SETUP)
        # AEDT 2025 R2 serializes the scripting API's PortsOnly:=True as
        # SolveType='PortsOnly', rather than retaining a PortsOnly=true key.
        receipt["native_ports_only_persisted"] = "SolveType='PortsOnly'" in section
        receipt["native_save_fields_persisted"] = "SaveAnyFields=true" in section
        receipt["single_setup_persisted"] = ("$begin 'Setup30GHz'" not in project_text)
        receipt["status"] = ("NATIVE_PORT_ONLY_MODEL_READY"
                             if receipt["native_ports_only_persisted"] and
                             receipt["single_setup_persisted"] else
                             "PORT_ONLY_SETTING_NOT_PERSISTED")
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    return 0 if receipt["status"] == "NATIVE_PORT_ONLY_MODEL_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
