"""Archive a solved AEDT project with results from a disposable saved copy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from license_environment import restore_ansys_environment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--setup", default="Setup30GHz",
                        help="Solved adaptive setup required before archiving")
    args = parser.parse_args()
    project = args.project.resolve()
    archive = args.archive.resolve()
    receipt = args.receipt.resolve()
    if not project.is_file() or not Path(str(project) + "results").is_dir():
        parser.error("Project and its solved result directory must both exist")
    if archive.exists() or receipt.exists():
        parser.error("Archive or receipt already exists")
    archive.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    record = {"project": str(project), "archive": str(archive),
              "setup": args.setup,
              "analysis_called": False, "status": "STARTED"}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        if f"{args.setup} : LastAdaptive" not in app.existing_analysis_sweeps:
            raise RuntimeError(f"The saved {args.setup} adaptive solution is not readable")
        result = app.archive_project(
            str(archive), include_external_files=True, include_results_file=True,
            notes="30 GHz, 20x10 mm feed, 60x20x60 mm horn, 12-mode HFSS solve")
        if not result or not archive.is_file() or archive.stat().st_size < 1_000_000:
            raise RuntimeError("AEDT did not create a nonempty results archive")
        digest = hashlib.sha256()
        with archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        record.update({"status": "ARCHIVED_WITH_RESULTS", "bytes": archive.stat().st_size,
                       "sha256": digest.hexdigest()})
        return 0
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        return 2
    finally:
        receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        if app is not None:
            try:
                app.release_desktop(close_projects=True, close_desktop=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
