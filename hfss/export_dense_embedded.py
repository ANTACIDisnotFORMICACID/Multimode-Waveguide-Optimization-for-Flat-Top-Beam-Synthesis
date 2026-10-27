"""Export a full-azimuth, complex HFSS modal basis from an existing solve.

Run this only on a copied .aedt + .aedtresults pair. No analysis or project
save is performed. The exported FFD basis is checked against the independent
four-cut report export before it can be used for synthesis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

import export_solved_in_gui as native
from license_environment import restore_ansys_environment


MODES = 12
THETA = np.arange(0.0, 90.0 + 0.5, 0.5)
PHI = np.arange(0.0, 360.0, 5.0)
SPHERE = "FullAzimuthSphere"
SETUP = "Setup30GHz : LastAdaptive"


def read_ffd(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with path.open(encoding="utf-8") as stream:
        first = stream.readline().split()
        second = stream.readline().split()
        frequencies = stream.readline().split()
        frequency = stream.readline().split()
        if len(first) != 3 or len(second) != 3 or frequencies != ["Frequencies", "1"]:
            raise ValueError(f"Unexpected FFD header: {path}")
        if frequency[:1] != ["Frequency"] or not np.isclose(float(frequency[1]), 30e9):
            raise ValueError(f"Unexpected FFD frequency: {path}")
        theta = np.linspace(float(first[0]), float(first[1]), int(first[2]))
        phi = np.linspace(float(second[0]), float(second[1]), int(second[2]))
        values = np.loadtxt(stream)
    if values.shape != (theta.size * phi.size, 4):
        raise ValueError(f"Unexpected FFD field shape: {path} {values.shape}")
    field = values.reshape(theta.size, phi.size, 4)
    complex_field = np.stack((field[..., 0] + 1j * field[..., 1],
                              field[..., 2] + 1j * field[..., 3]), axis=-1)
    if not np.isfinite(complex_field).all():
        raise ValueError(f"Non-finite FFD field: {path}")
    return theta, phi, complex_field


def read_mapping(path: Path) -> dict[int, Path]:
    mapping = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if fields and fields[0].startswith("WavePort1:"):
            index = int(fields[0].split(":", 1)[1])
            mapping[index] = path.parent / (fields[1] + ".ffd")
    if set(mapping) != set(range(1, MODES + 1)):
        raise ValueError("The embedded-pattern map does not contain all 12 modes")
    return mapping


def compare_original_cuts(fields: np.ndarray, original: Path) -> dict[str, float]:
    samples = {}
    with original.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            mode = int(row["PortMode"])
            theta = float(row["ThetaDeg"])
            phi = int(row["PhiDeg"])
            samples[mode, theta, phi] = np.array([
                complex(float(row["EThetaReal"]), float(row["EThetaImag"])),
                complex(float(row["EPhiReal"]), float(row["EPhiImag"])),
            ])
    residual = 0.0
    reference = 0.0
    maximum = 0.0
    for (mode, theta, phi), old in samples.items():
        ti = int(round(theta / 0.5))
        pi = int(round(phi / 5))
        new = fields[mode - 1, ti, pi] * 1000.0
        delta = np.linalg.norm(new - old)
        residual += float(delta**2)
        reference += float(np.linalg.norm(old)**2)
        maximum = max(maximum, float(delta))
    if len(samples) != MODES * THETA.size * 4:
        raise ValueError("The original four-cut reference has missing samples")
    error = float(np.sqrt(residual / reference))
    if error > 1e-7:
        raise ValueError(f"Dense FFD disagrees with original report cuts: {error:.3g}")
    return {"sample_count": len(samples), "relative_complex_l2_error": error,
            "maximum_absolute_report_unit_error": maximum,
            "empirical_ffd_to_report_factor": 1000.0}


def select_intrinsic_single_mode(solution_module, selected: int) -> None:
    settings = [["IncludePortPostProcessing:=", False,
                 "SpecifySystemPower:=", False]]
    for mode in range(1, MODES + 1):
        settings.append(["Name:=", f"WavePort1:{mode}",
                         "Magnitude:=", "1W" if mode == selected else "0W",
                         "Phase:=", "0deg"])
    solution_module.EditSources(settings)


def compare_intrinsic_live_cuts(app, fields: np.ndarray,
                                setup: str) -> dict[str, float]:
    solution = app.odesign.GetModule("Solutions")
    report = app.odesign.GetModule("ReportSetup")
    expressions = ["re(rETheta)", "im(rETheta)", "re(rEPhi)", "im(rEPhi)"]
    residual = 0.0
    reference = 0.0
    sample_count = 0
    for mode in range(1, MODES + 1):
        select_intrinsic_single_mode(solution, mode)
        for phi_deg in (0, 90, 180, 270):
            raw = report.GetSolutionDataPerVariation(
                "Far Fields", setup, ["Context:=", "OpenApertureSphere"],
                ["Freq:=", ["30GHz"], "Theta:=", ["All"],
                 "Phi:=", [f"{phi_deg}deg"]], expressions)
            variations = list(raw)
            if len(variations) != 1:
                raise ValueError("Expected one intrinsic far-field variation")
            item = variations[0]
            theta = np.asarray(item.GetSweepValues("Theta", False), dtype=float)
            if not np.allclose(theta, THETA):
                raise ValueError("Original report theta grid differs")
            values = [np.asarray(item.GetRealDataValues(expr, False), dtype=float)
                      for expr in expressions]
            reported = np.stack((values[0] + 1j * values[1],
                                 values[2] + 1j * values[3]), axis=-1)
            expected = fields[mode - 1, :, phi_deg // 5, :] * 1000.0
            residual += float(np.linalg.norm(reported - expected)**2)
            reference += float(np.linalg.norm(reported)**2)
            sample_count += len(theta)
    error = float(np.sqrt(residual / reference))
    if error > 1e-7:
        raise ValueError(f"Intrinsic FFD disagrees with direct HFSS reports: {error:.3g}")
    return {"sample_count": sample_count, "relative_complex_l2_error": error,
            "empirical_ffd_to_report_factor": 1000.0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="A COPY of the solved .aedt project")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("original_cuts", type=Path, nargs="?",
                        help="Required for the original 50-ohm-postprocessed export")
    parser.add_argument("--intrinsic", action="store_true",
                        help="Use the intrinsic modal-port reference without 50-ohm post-processing")
    parser.add_argument("--setup", default=SETUP,
                        help="Solved HFSS setup, e.g. 'PowerCheck30GHz : LastAdaptive'")
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output_dir.resolve()
    if not project.is_file() or not Path(str(project) + "results").is_dir():
        parser.error("Project and matching .aedtresults must both exist")
    if output.exists():
        parser.error("Output already exists; refusing to overwrite")
    if not args.intrinsic and (args.original_cuts is None or
                               not args.original_cuts.is_file()):
        parser.error("Original four-cut report CSV is required for postprocessed export")
    output.mkdir(parents=True)
    native_dir = output / "native_ffd"
    native_dir.mkdir()
    receipt = {"status": "RUNNING", "project": str(project),
               "analysis_called": False, "project_saved": False,
               "source_setting": "WavePort1:1=1W; other 11 modes=0W",
               "setup": args.setup,
               "include_port_post_processing": not args.intrinsic,
               "source_reference": "intrinsic_modal" if args.intrinsic else "50_ohm_postprocessed"}
    app = None
    try:
        restore_ansys_environment()
        from ansys.aedt.core import Hfss

        app = Hfss(project=str(project), design="OpenEndedWaveguide",
                   version="2025.2", non_graphical=True, new_desktop=True,
                   close_on_exit=True, remove_lock=False)
        if args.setup not in app.existing_analysis_sweeps:
            raise RuntimeError(f"The saved full-wave solution is unavailable: {args.setup}")
        sphere = app.insert_infinite_sphere(
            definition="Theta-Phi", x_start=0, x_stop=90, x_step=0.5,
            y_start=0, y_stop=355, y_step=5, name=SPHERE)
        if not sphere:
            raise RuntimeError("Could not add the full-azimuth far-field sphere")
        if args.intrinsic:
            select_intrinsic_single_mode(app.odesign.GetModule("Solutions"), 1)
        else:
            native.PORT_MODES = MODES
            native.select_single_mode(app.odesign.GetModule("Solutions"), 1)
        design = app.odesign
        design.GetModule("RadField").ExportElementPatternToFile([
            "ExportFileName:=", str(native_dir / "eep.ffd"),
            "SetupName:=", SPHERE,
            "IntrinsicVariationKey:=", "Freq='30GHz'",
            "DesignVariationKey:=", design.GetNominalVariation(),
            "SolutionName:=", args.setup,
        ])
        mapping = read_mapping(native_dir / "eep.txt")
        fields = np.empty((MODES, THETA.size, PHI.size, 2), dtype=np.complex128)
        hashes = {}
        for mode, path in sorted(mapping.items()):
            theta, phi, field = read_ffd(path)
            if not np.allclose(theta, THETA) or not np.allclose(phi, PHI):
                raise ValueError(f"Unexpected angular grid for mode {mode}")
            fields[mode - 1] = field
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if args.intrinsic:
            receipt["live_cut_comparison"] = compare_intrinsic_live_cuts(
                app, fields, args.setup)
        else:
            receipt["original_cut_comparison"] = compare_original_cuts(
                fields, args.original_cuts.resolve())
        np.savez_compressed(output / "complex_modal_basis.npz",
                            theta_deg=THETA, phi_deg=PHI,
                            port_modes=np.arange(1, MODES + 1),
                            e_theta=fields[..., 0], e_phi=fields[..., 1])
        receipt.update({"status": "FULL_AZIMUTH_EXPORTED_AND_CROSSCHECKED",
                        "theta_samples": int(THETA.size), "phi_samples": int(PHI.size),
                        "mode_count": MODES, "ffd_sha256": hashes,
                        "array_shape": list(fields.shape)})
        return 0
    except Exception as exc:
        receipt.update({"status": "FAILED", "error": repr(exc)})
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n",
                                             encoding="utf-8")
        if app is not None:
            app.release_desktop(close_projects=True, close_desktop=True)


if __name__ == "__main__":
    raise SystemExit(main())
