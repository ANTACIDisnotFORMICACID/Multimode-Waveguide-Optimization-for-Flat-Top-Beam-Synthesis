"""Probe complex 3D field grids just inside an HFSS wave port.

The sampled 3D field includes incident and reflected waves. It is *not*
itself the pure 2D port eigenfield, so this script does not identify modes.
Run only on a fresh disposable copy of a solved project.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

import export_solved_in_gui as native_exporter
from license_environment import restore_ansys_environment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--port-mode", type=int, default=1)
    parser.add_argument("--all-modes", action="store_true")
    parser.add_argument("--port-modes", type=int, choices=(10, 12), default=10)
    parser.add_argument("--plane-z-mm", type=float, default=-99.9)
    args = parser.parse_args()
    if not 1 <= args.port_mode <= args.port_modes:
        parser.error("--port-mode must be within the configured port count")
    project = args.project.resolve()
    if not project.is_file():
        parser.error("Project does not exist")
    root = Path(os.environ.get("TEMP", r"C:\Temp")) / "waveguide_farfield_hfss"
    output = root / ("port_field_export_" + time.strftime("%Y%m%dT%H%M%S"))
    if output.exists():
        parser.error("Output already exists")
    output.mkdir(parents=True)
    receipt = {"status": "RUNNING", "project": str(project),
               "port_modes": list(range(1, args.port_modes + 1)) if args.all_modes else [args.port_mode],
               "plane_z_mm": args.plane_z_mm,
               "field_type": "3D_TOTAL_E_NOT_2D_PORT_EIGENFIELD",
               "analysis_called": False, "project_saved": False,
               "fields": []}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        native_exporter.PORT_MODES = args.port_modes
        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        if not app.setups[0].is_solved:
            raise RuntimeError("No readable adaptive solution in this disposable copy")
        for mode in receipt["port_modes"]:
            field_file = output / f"total_E_port_mode_{mode}.fld"
            native_exporter.select_single_mode(app.odesign.GetModule("Solutions"), mode)
            result = app.post.export_field_file_on_grid(
                "E", solution="Setup30GHz : LastAdaptive", file_name=str(field_file),
                grid_type="Cartesian", grid_start=[-9, -4.5, args.plane_z_mm],
                grid_stop=[9, 4.5, args.plane_z_mm], grid_step=[1, 0.5, 0],
                is_vector=True, intrinsics={"Freq": "30GHz", "Phase": "0deg"},
                export_with_sample_points=True, export_in_si_system=False,
            )
            if not result or not field_file.is_file() or field_file.stat().st_size < 100:
                raise RuntimeError(f"HFSS did not export a nonempty field grid for mode {mode}")
            with field_file.open(encoding="utf-8", errors="replace") as stream:
                header = [stream.readline().strip(), stream.readline().strip()]
            receipt["fields"].append({"port_mode": mode, "field_file": str(field_file),
                                      "file_bytes": field_file.stat().st_size,
                                      "field_header": header})
        receipt["status"] = "GRIDS_EXPORTED_UNVERIFIED"
        return 0
    except Exception as exc:
        receipt["status"] = "FAILED"
        receipt["error"] = repr(exc)
        receipt["traceback"] = traceback.format_exc()
        return 2
    finally:
        (output / "probe_receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print("HFSS port field probe: " + str(output / "probe_receipt.json"))
        if app is not None:
            try:
                app.release_desktop(close_projects=True, close_desktop=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
