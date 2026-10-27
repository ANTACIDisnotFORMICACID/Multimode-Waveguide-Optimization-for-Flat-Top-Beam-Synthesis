"""Back up an unlocked AEDT project and results without launching AEDT.

This is an ordinary ZIP backup, not an AEDT-native .aedtz archive. Restore by
extracting the project file and its matching .aedtresults directory together.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    results = Path(str(project) + "results")
    archive = args.archive.resolve()
    receipt = args.receipt.resolve()
    partial = archive.with_name(archive.name + ".partial")
    if project.suffix.lower() != ".aedt" or not project.is_file() or not results.is_dir():
        parser.error("An .aedt file and matching .aedtresults directory are required")
    if Path(str(project) + ".lock").exists():
        parser.error("Close the AEDT project before archiving")
    if any(path.exists() for path in (archive, partial, receipt)):
        parser.error("Archive, partial archive, or receipt already exists")
    files = [project] + sorted(path for path in results.rglob("*") if path.is_file())
    source_bytes = sum(path.stat().st_size for path in files)
    archive.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    record = {"status": "STARTED", "project": str(project),
              "results": str(results), "archive": str(archive),
              "format": "ordinary_zip_not_aedtz", "source_file_count": len(files),
              "source_bytes": source_bytes, "analysis_called": False}
    try:
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=1, allowZip64=True) as output:
            for path in files:
                if path == project:
                    member = project.name
                else:
                    member = f"{results.name}/{path.relative_to(results).as_posix()}"
                output.write(path, member)
        with zipfile.ZipFile(partial) as check:
            if len(check.infolist()) != len(files):
                raise RuntimeError("Archive member count differs from source")
            bad_member = check.testzip()
            if bad_member is not None:
                raise RuntimeError(f"ZIP CRC check failed: {bad_member}")
            archived_bytes = sum(item.file_size for item in check.infolist())
            if archived_bytes != source_bytes:
                raise RuntimeError("Archive uncompressed byte count differs from source")
        digest = hashlib.sha256()
        with partial.open("rb") as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        partial.replace(archive)
        record.update({"status": "RAW_RESULTS_ARCHIVED_AND_CRC_CHECKED",
                       "archive_bytes": archive.stat().st_size,
                       "sha256": digest.hexdigest(),
                       "uncompressed_bytes": archived_bytes})
        return 0
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
