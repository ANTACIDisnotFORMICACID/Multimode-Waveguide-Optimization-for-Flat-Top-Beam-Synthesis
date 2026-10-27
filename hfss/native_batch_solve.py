"""Run AEDT's documented native BatchSolve on an isolated project copy.

This path avoids PyAEDT/gRPC Analyze. It never solves or overwrites the
repository project; the English-path batch copy and all results are retained.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from license_environment import restore_ansys_environment


AEDT = Path(r"D:\Program Files\ANSYS Inc\v252\AnsysEM\ansysedt.exe")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--timeout-minutes", type=int, default=30)
    args = parser.parse_args()
    source = args.project.resolve()
    if not source.is_file() or not AEDT.is_file():
        parser.error("Project or AEDT executable not found")
    root = Path(os.environ.get("TEMP", r"C:\Temp")) / "waveguide_farfield_hfss"
    root.mkdir(parents=True, exist_ok=True)
    run_dir = root / ("native_batch_12mode_" + time.strftime("%Y%m%dT%H%M%S"))
    if run_dir.exists():
        parser.error("Batch directory already exists")
    run_dir.mkdir()
    project = run_dir / "waveguide_30ghz_12mode.aedt"
    shutil.copy2(source, project)
    log_path = run_dir / "batch_console.log"
    aedt_log = run_dir / "aedt_batch.log"
    receipt_path = run_dir / "batch_receipt.json"
    command = [str(AEDT), "-Iconic", "-Monitor", "-LogFile", str(aedt_log),
               "-BatchSolve", "OpenEndedWaveguide:Nominal:Setup30GHz", str(project)]
    receipt = {"status": "RUNNING", "source_project": str(source),
               "batch_project": str(project), "console_log": str(log_path),
               "aedt_log": str(aedt_log), "timeout_minutes": args.timeout_minutes,
               "command_flags": command[1:-1]}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("HFSS native batch directory: " + str(run_dir), flush=True)
    print("HFSS native batch receipt: " + str(receipt_path), flush=True)
    restore_ansys_environment()
    started = time.time()
    try:
        with log_path.open("wb") as stream:
            completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                       timeout=args.timeout_minutes * 60, check=False)
        receipt["exit_code"] = completed.returncode
        messages = aedt_log.read_text(encoding="utf-8", errors="replace") if aedt_log.is_file() else ""
        receipt["normal_completion_message"] = "Normal completion of simulation" in messages
        receipt["solver_engine_error"] = "Engine terminated unexpectedly" in messages
        results = project.with_suffix(".aedtresults") / "OpenEndedWaveguide.results"
        receipt["result_file_count"] = sum(1 for item in results.rglob("*") if item.is_file()) if results.is_dir() else 0
        receipt["status"] = ("SOLVED_UNVERIFIED" if completed.returncode == 0 and
                             receipt["normal_completion_message"] and
                             not receipt["solver_engine_error"] and
                             receipt["result_file_count"] > 10 else "SOLVER_FAILED")
    except subprocess.TimeoutExpired:
        receipt["status"] = "TIMED_OUT"
        receipt["exit_code"] = None
    finally:
        receipt["elapsed_seconds"] = time.time() - started
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return 0 if receipt["status"] == "SOLVED_UNVERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
