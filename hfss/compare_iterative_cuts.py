"""Compare 12-pass and 15-pass intrinsic vector fields on four HFSS rays.

The baseline is the independently cross-checked 12-pass full-azimuth FFD
basis. The new data are direct HFSS report cuts exported inside the GUI.
This comparison concerns normalized shape and complex modal consistency,
not absolute antenna efficiency or full-azimuth convergence.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from verify_composite_sources import read_weights


PHIS = (0, 90, 180, 270)
THETA = np.arange(0.0, 90.0 + 0.5, 0.5)


def read_new_cuts(path: Path) -> np.ndarray:
    fields = np.full((12, 4, THETA.size, 2), np.nan + 1j * np.nan,
                     dtype=np.complex128)
    seen = set()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            mode = int(row["PortMode"])
            phi = int(row["PhiDeg"])
            theta = float(row["ThetaDeg"])
            if not 1 <= mode <= 12 or phi not in PHIS:
                raise ValueError(f"Invalid port mode or azimuth: {mode}, {phi}")
            theta_index = int(round(theta / 0.5))
            if (not 0 <= theta_index < THETA.size or
                    abs(THETA[theta_index] - theta) > 1e-6):
                raise ValueError(f"Unexpected theta grid: {theta}")
            key = (mode, phi, theta_index)
            if key in seen:
                raise ValueError(f"Duplicate field sample: {key}")
            seen.add(key)
            fields[mode - 1, PHIS.index(phi), theta_index, 0] = complex(
                float(row["EThetaReal"]), float(row["EThetaImag"]))
            fields[mode - 1, PHIS.index(phi), theta_index, 1] = complex(
                float(row["EPhiReal"]), float(row["EPhiImag"]))
    if len(seen) != fields.shape[0] * fields.shape[1] * fields.shape[2]:
        raise ValueError(f"Expected 8688 complex field samples, got {len(seen)}")
    if not np.isfinite(fields).all():
        raise ValueError("Non-finite complex field sample")
    return fields


def read_old_cuts(path: Path) -> np.ndarray:
    with np.load(path) as source:
        theta = source["theta_deg"]
        phi = source["phi_deg"]
        ports = source["port_modes"]
        if (not np.array_equal(theta, THETA) or
                not np.array_equal(phi, np.arange(0, 360, 5)) or
                not np.array_equal(ports, np.arange(1, 13))):
            raise ValueError("Baseline full-azimuth grid or port order differs")
        # The 12-pass live report was checked against FFD * 1000.
        fields = np.stack((source["e_theta"], source["e_phi"]), axis=-1)
        return np.transpose(fields[:, :, [angle // 5 for angle in PHIS], :],
                            (0, 2, 1, 3)) * 1000.0


def normalized_db(field: np.ndarray) -> np.ndarray:
    amplitude = np.linalg.norm(field, axis=-1)
    maximum = float(amplitude.max())
    if maximum <= 0:
        raise ValueError("Zero composite field")
    return 20 * np.log10(np.maximum(amplitude / maximum, 1e-12))


def near_cutoff_subspace(old: np.ndarray, new: np.ndarray) -> dict:
    earlier = old[10:12].reshape(2, -1)
    later = new[10:12].reshape(2, -1)
    coefficient = np.array([
        [np.vdot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))
         for y in later] for x in earlier])
    old_basis, _ = np.linalg.qr(earlier.T)
    new_basis, _ = np.linalg.qr(later.T)
    principal_cosines = np.linalg.svd(
        old_basis.conj().T @ new_basis, compute_uv=False)
    return {"port_modes": [11, 12],
            "cross_correlation_magnitude": np.abs(coefficient).tolist(),
            "cross_correlation_phase_deg": np.angle(coefficient, deg=True).tolist(),
            "subspace_principal_cosines": principal_cosines.tolist(),
            "interpretation": "Mode labels rotate within the near-cutoff pair; the two-dimensional field subspace remains nearly unchanged."}


def summarize(old: np.ndarray, new: np.ndarray, weights: np.ndarray) -> dict:
    old_sum = np.tensordot(weights, old, axes=(0, 0))
    new_sum = np.tensordot(weights, new, axes=(0, 0))
    old_db, new_db = normalized_db(old_sum), normalized_db(new_sum)
    visible = (old_db > -20) | (new_db > -20)
    main = THETA <= 20
    outside = THETA >= 40
    return {
        "normalized_rmse_db_above_minus20": float(np.sqrt(np.mean(
            (old_db[visible] - new_db[visible]) ** 2))),
        "visible_sample_count": int(visible.sum()),
        "old_four_ray_main_ripple_db": float(old_db[:, main].max() - old_db[:, main].min()),
        "new_four_ray_main_ripple_db": float(new_db[:, main].max() - new_db[:, main].min()),
        "old_four_ray_outside_max_db": float(old_db[:, outside].max()),
        "new_four_ray_outside_max_db": float(new_db[:, outside].max()),
        "old_peak_phi_deg": PHIS[int(np.unravel_index(np.argmax(old_db), old_db.shape)[0])],
        "new_peak_phi_deg": PHIS[int(np.unravel_index(np.argmax(new_db), new_db.shape)[0])],
        "old_peak_theta_deg": float(THETA[np.unravel_index(np.argmax(old_db), old_db.shape)[1]]),
        "new_peak_theta_deg": float(THETA[np.unravel_index(np.argmax(new_db), new_db.shape)[1]]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_basis", type=Path)
    parser.add_argument("new_cuts", type=Path)
    parser.add_argument("weights", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    old = read_old_cuts(args.baseline_basis)
    new = read_new_cuts(args.new_cuts)
    correlations = []
    for mode in range(12):
        earlier = old[mode].ravel()
        later = new[mode].ravel()
        coefficient = np.vdot(earlier, later) / (
            np.linalg.norm(earlier) * np.linalg.norm(later))
        correlations.append({"port_mode": mode + 1,
                             "four_ray_field_correlation_magnitude": float(abs(coefficient)),
                             "four_ray_phase_shift_deg": float(np.rad2deg(np.angle(coefficient))),
                             "four_ray_field_norm_ratio": float(
                                 np.linalg.norm(later) / np.linalg.norm(earlier))})
    single = np.zeros(12, dtype=np.complex128)
    single[0] = 1.0
    cases = (("port 1", single),
             ("ports 1+5+8 fixed intrinsic weights", read_weights(args.weights)))
    patterns = [{"case": name, **summarize(old, new, weights)}
                for name, weights in cases]
    output = args.output_dir
    output.mkdir(parents=True)
    for filename, rows in (("modal_correlation.csv", correlations),
                           ("four_ray_pattern_comparison.csv", patterns)):
        with (output / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (output / "near_cutoff_pair_mixing.json").write_text(
        json.dumps(near_cutoff_subspace(old, new), indent=2) + "\n",
        encoding="utf-8")
    (output / "receipt.json").write_text(json.dumps({
        "status": "FOUR_RAY_COMPLEX_COMPARISON_EXPORTED",
        "baseline_basis": str(args.baseline_basis.resolve()),
        "new_cuts": str(args.new_cuts.resolve()),
        "weights": str(args.weights.resolve()),
        "source_reference": "intrinsic_modal",
        "analysis_called": False,
        "scope": "Four azimuth rays only; does not certify full-azimuth pattern or absolute efficiency",
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
