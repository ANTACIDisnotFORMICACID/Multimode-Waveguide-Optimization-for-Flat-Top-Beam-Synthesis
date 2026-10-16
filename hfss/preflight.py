"""Read-only dependency and installation preflight for the HFSS workflow."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.project_root.resolve()
    executable = Path(r"D:\Program Files\ANSYS Inc\v252\AnsysEM\ansysedt.exe")
    discovered_by_environment = bool(os.environ.get("ANSYSEM_ROOT252"))
    status = {
        "python": sys.version,
        "pyaedt_available": importlib.util.find_spec("pyaedt") is not None,
        "ansys_aedt_2025_r2_executable": str(executable),
        "ansys_aedt_2025_r2_installed": executable.is_file(),
        "ansysem_root252_was_set": discovered_by_environment,
        "license_verified": False,
        "note": "Installation checks do not prove that an HFSS solver license can be checked out.",
    }
    output = root / "results" / "hfss"
    output.mkdir(parents=True, exist_ok=True)
    (output / "preflight.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0 if status["pyaedt_available"] and status["ansys_aedt_2025_r2_installed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
