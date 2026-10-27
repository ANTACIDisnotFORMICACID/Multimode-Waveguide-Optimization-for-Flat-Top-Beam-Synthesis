"""Compare intrinsic and 50-ohm-postprocessed HFSS antenna power reports."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from license_environment import restore_ansys_environment
from verify_composite_sources import read_weights


QUANTITIES = ("IncidentPower", "AcceptedPower", "RadiatedPower",
              "RadiationEfficiency", "PeakRealizedGain")


def weights_for_cases(two_mode_summary: Path, three_mode_weights: Path,
                      intrinsic_three_weights: Path | None = None) -> dict[str, np.ndarray]:
    cases = {}
    for mode in (1, 8, 11, 12):
        w = np.zeros(12, dtype=np.complex128)
        w[mode - 1] = 1
        cases[f"port {mode}"] = w
    optimum = json.loads(two_mode_summary.read_text(encoding="utf-8"))["best"]
    w = np.zeros(12, dtype=np.complex128)
    w[0] = 1
    w[7] = optimum["Ratio"] * np.exp(1j * np.deg2rad(optimum["PhaseDeg"]))
    cases["ports 1+8 E/H optimized"] = w / np.linalg.norm(w)
    cases["ports 1+5+8 2D optimized"] = read_weights(three_mode_weights)
    if intrinsic_three_weights is not None:
        cases["ports 1+5+8 2D intrinsic optimized"] = read_weights(intrinsic_three_weights)
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("two_mode_summary", type=Path)
    parser.add_argument("three_mode_weights", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--intrinsic-three-weights", type=Path)
    parser.add_argument("--setup", default="Setup30GHz",
                        help="Solved HFSS adaptive setup to audit")
    parser.add_argument("--sphere", default="OpenApertureSphere",
                        help="Far-field infinite sphere for antenna parameters")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    project = args.project.resolve()
    if not project.is_file() or not Path(str(project) + "results").is_dir():
        parser.error("A copied solved project and matching results are required")
    cases = weights_for_cases(args.two_mode_summary, args.three_mode_weights,
                             args.intrinsic_three_weights)
    args.output_dir.mkdir(parents=True)
    receipt = {"status": "RUNNING", "analysis_called": False,
               "project_saved": False, "project": str(project),
               "setup": args.setup, "sphere": args.sphere}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        sweep = f"{args.setup} : LastAdaptive"
        if sweep not in app.existing_analysis_sweeps:
            raise RuntimeError(f"Saved HFSS solution unavailable: {sweep}")
        solution = app.odesign.GetModule("Solutions")
        report = app.odesign.GetModule("ReportSetup")
        rows = []
        for name, w in cases.items():
            for include in (False, True):
                settings = [["IncludePortPostProcessing:=", include,
                             "SpecifySystemPower:=", False]]
                for mode, value in enumerate(w, 1):
                    settings.append(["Name:=", f"WavePort1:{mode}",
                                     "Magnitude:=", f"{abs(value)**2:.15g}W",
                                     "Phase:=", f"{np.rad2deg(np.angle(value)):.15g}deg"])
                solution.EditSources(settings)
                raw = report.GetSolutionDataPerVariation(
                    "Antenna Parameters", sweep,
                    ["Context:=", args.sphere],
                    ["Freq:=", ["30GHz"]], list(QUANTITIES))
                variations = list(raw)
                if len(variations) != 1:
                    raise ValueError("Expected one antenna-parameter variation")
                data = variations[0]
                powers = {key: float(list(data.GetRealDataValues(key, False))[0])
                          for key in QUANTITIES}
                rows.append({"case": name, "include_port_post_processing": include,
                             **powers})
                print(name, "postproc", include, powers, flush=True)
        with (args.output_dir / "native_power_comparison.csv").open(
                "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        receipt.update({"status": "NATIVE_POWER_EXPORTED", "case_count": len(cases),
                        "row_count": len(rows),
                        "warning": "Radiation efficiency above unity indicates that radiated-power accuracy or reference consistency needs investigation; do not claim absolute efficiency."})
        return 0
    except Exception as exc:
        receipt.update({"status": "FAILED", "error": repr(exc)})
        raise
    finally:
        (args.output_dir / "receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if app is not None:
            app.release_desktop(close_projects=True, close_desktop=True)


if __name__ == "__main__":
    raise SystemExit(main())
