"""Verify an optimized modal sum against AEDT EditSources post-processing.

The existing full-wave solve is read from a copied project. This checks complex
Etheta/Ephi, not only normalized dB patterns. No Analyze or Save is invoked.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from license_environment import restore_ansys_environment


def read_weights(path: Path) -> np.ndarray:
    weights = np.zeros(12, dtype=np.complex128)
    seen = set()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            mode = int(row["PortMode"])
            if mode in seen or not 1 <= mode <= 12:
                raise ValueError("Invalid or duplicated port mode")
            seen.add(mode)
            weights[mode - 1] = float(row["Amplitude"]) * np.exp(
                1j * np.deg2rad(float(row["PhaseDeg"])))
    if not seen or not np.isclose(np.linalg.norm(weights), 1.0, atol=1e-9):
        raise ValueError("Weights must describe 1 W total incident modal power")
    return weights


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("basis", type=Path)
    parser.add_argument("weights", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--intrinsic", action="store_true",
                        help="Turn off 50-ohm port post-processing in EditSources")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    project = args.project.resolve()
    if not project.is_file() or not Path(str(project) + "results").is_dir():
        parser.error("A copied solved project and its .aedtresults are required")
    with np.load(args.basis) as archive:
        basis = {key: archive[key] for key in archive.files}
    weights = read_weights(args.weights)
    output = args.output_dir.resolve()
    output.mkdir(parents=True)
    receipt = {"status": "RUNNING", "analysis_called": False, "project_saved": False,
               "project": str(project), "weights_csv": str(args.weights.resolve()),
               "basis": str(args.basis.resolve()),
               "include_port_post_processing": not args.intrinsic}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        if "Setup30GHz : LastAdaptive" not in app.existing_analysis_sweeps:
            raise RuntimeError("Saved HFSS solution is unavailable")
        sphere = app.insert_infinite_sphere(
            definition="Theta-Phi", x_start=0, x_stop=90, x_step=10,
            y_start=0, y_stop=315, y_step=45, name="CompositeCheckSphere")
        if not sphere:
            raise RuntimeError("Composite-check far-field sphere failed")
        settings = [["IncludePortPostProcessing:=", not args.intrinsic,
                     "SpecifySystemPower:=", False]]
        for mode, w in enumerate(weights, 1):
            settings.append(["Name:=", f"WavePort1:{mode}",
                             "Magnitude:=", f"{abs(w)**2:.15g}W",
                             "Phase:=", f"{np.rad2deg(np.angle(w)):.15g}deg"])
        app.odesign.GetModule("Solutions").EditSources(settings)
        report = app.odesign.GetModule("ReportSetup")
        expressions = ["re(rETheta)", "im(rETheta)", "re(rEPhi)", "im(rEPhi)"]
        residual = 0.0
        reference = 0.0
        rows = []
        for phi_deg in range(0, 360, 45):
            raw = report.GetSolutionDataPerVariation(
                "Far Fields", "Setup30GHz : LastAdaptive",
                ["Context:=", "CompositeCheckSphere"],
                ["Freq:=", ["30GHz"], "Theta:=", ["All"],
                 "Phi:=", [f"{phi_deg}deg"]], expressions)
            variations = list(raw)
            if len(variations) != 1:
                raise ValueError("Expected exactly one far-field variation")
            values = variations[0]
            theta_deg = np.asarray(values.GetSweepValues("Theta", False), dtype=float)
            components = [np.asarray(values.GetRealDataValues(expr, False), dtype=float)
                          for expr in expressions]
            reported = np.stack((components[0] + 1j * components[1],
                                 components[2] + 1j * components[3]), axis=-1)
            ti = np.rint(theta_deg / 0.5).astype(int)
            pi = phi_deg // 5
            expected = np.einsum(
                "m,mtc->tc", weights,
                np.stack((basis["e_theta"][:, ti, pi],
                          basis["e_phi"][:, ti, pi]), axis=-1)) * 1000.0
            residual += float(np.linalg.norm(reported - expected)**2)
            reference += float(np.linalg.norm(expected)**2)
            for theta, actual, prediction in zip(theta_deg, reported, expected):
                rows.append([theta, phi_deg, actual[0].real, actual[0].imag,
                             prediction[0].real, prediction[0].imag,
                             actual[1].real, actual[1].imag,
                             prediction[1].real, prediction[1].imag])
        error = float(np.sqrt(residual / reference))
        receipt.update({"sample_count": len(rows),
                        "complex_relative_l2_error": error,
                        "source_magnitudes_w": [float(abs(w)**2) for w in weights],
                        "source_phases_deg": [float(np.rad2deg(np.angle(w))) for w in weights],
                        "status": "COMPOSITE_FIELD_MATCHED" if error < 1e-6 else
                                  "COMPOSITE_FIELD_MISMATCH"})
        with (output / "complex_field_check.csv").open(
                "w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["ThetaDeg", "PhiDeg", "ActualThetaReal", "ActualThetaImag",
                             "ExpectedThetaReal", "ExpectedThetaImag",
                             "ActualPhiReal", "ActualPhiImag",
                             "ExpectedPhiReal", "ExpectedPhiImag"])
            writer.writerows(rows)
        if error >= 1e-6:
            raise ValueError(f"HFSS composite field differs from modal sum: {error:.3g}")
        return 0
    except Exception as exc:
        receipt["error"] = repr(exc)
        if receipt["status"] == "RUNNING":
            receipt["status"] = "FAILED"
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n",
                                             encoding="utf-8")
        if app is not None:
            app.release_desktop(close_projects=True, close_desktop=True)


if __name__ == "__main__":
    raise SystemExit(main())
