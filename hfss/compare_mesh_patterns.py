"""Compare native modal fields and normalized patterns across HFSS meshes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from analyze_full_azimuth import evaluate
from verify_composite_sources import read_weights


def load_basis(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as archive:
        data = {key: archive[key] for key in archive.files}
    if data["e_theta"].shape != (12, 181, 72):
        raise ValueError(f"Unexpected modal basis shape: {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_basis", type=Path)
    parser.add_argument("refined_basis", type=Path)
    parser.add_argument("three_mode_weights", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    baseline = load_basis(args.baseline_basis)
    refined = load_basis(args.refined_basis)
    for key in ("theta_deg", "phi_deg", "port_modes"):
        if not np.array_equal(baseline[key], refined[key]):
            raise ValueError(f"Different {key} grids or port indices")
    old_fields = np.stack((baseline["e_theta"], baseline["e_phi"]), axis=-1)
    new_fields = np.stack((refined["e_theta"], refined["e_phi"]), axis=-1)
    correlations = []
    for mode in range(12):
        old = old_fields[mode].ravel()
        new = new_fields[mode].ravel()
        correlation = np.vdot(old, new) / (np.linalg.norm(old) * np.linalg.norm(new))
        correlations.append({"port_mode": mode + 1,
                             "field_correlation_magnitude": float(abs(correlation)),
                             "field_phase_shift_deg": float(np.rad2deg(np.angle(correlation))),
                             "field_norm_ratio": float(np.linalg.norm(new) / np.linalg.norm(old))})
    one = np.zeros(12, dtype=np.complex128)
    one[0] = 1
    three = read_weights(args.three_mode_weights)
    rows = []
    for name, weights in (("port 1", one), ("ports 1+5+8 intrinsic optimum", three)):
        old_metrics, old_db = evaluate(baseline, None, weights)
        new_metrics, new_db = evaluate(refined, None, weights)
        region = (old_db > -20) | (new_db > -20)
        rows.append({"case": name,
                     "baseline_main_disk_ripple_db": old_metrics["main_disk_ripple_db"],
                     "refined_main_disk_ripple_db": new_metrics["main_disk_ripple_db"],
                     "baseline_outside_disk_db": old_metrics["outside_disk_db"],
                     "refined_outside_disk_db": new_metrics["outside_disk_db"],
                     "baseline_peak_theta_deg": old_metrics["peak_theta_deg"],
                     "refined_peak_theta_deg": new_metrics["peak_theta_deg"],
                     "normalized_pattern_rmse_db_above_minus20": float(np.sqrt(
                         np.mean((old_db[region] - new_db[region])**2))),
                     "sample_count_above_minus20": int(np.count_nonzero(region))})
    args.output_dir.mkdir(parents=True)
    for name, table in (("modal_field_correlation.csv", correlations),
                        ("mesh_pattern_comparison.csv", rows)):
        with (args.output_dir / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    (args.output_dir / "receipt.json").write_text(json.dumps({
        "status": "MESH_PATTERN_COMPARISON_EXPORTED",
        "baseline_basis": str(args.baseline_basis),
        "refined_basis": str(args.refined_basis),
        "weights": str(args.three_mode_weights),
        "caveat": "The refined solve reached its adaptive pass cap before three consecutive MaxDeltaS passes.",
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
