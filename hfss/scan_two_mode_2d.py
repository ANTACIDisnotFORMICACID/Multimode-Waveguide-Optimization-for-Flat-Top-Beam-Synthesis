"""Scan TE10 plus each HFSS port mode with a full-azimuth objective.

Port numbers are retained because degenerate TE/TM pairs have not yet been
identified from pure two-dimensional port eigenfields.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution

from analyze_full_azimuth import evaluate, load_s_matrix


def objective(fields: np.ndarray, theta: np.ndarray, phi: np.ndarray,
              ratio: float, phase: float) -> float:
    weights = np.array([1, ratio * np.exp(1j * phase)]) / np.sqrt(1 + ratio**2)
    return objective_from_weights(fields, theta, phi, weights)


def objective_from_weights(fields: np.ndarray, theta: np.ndarray, phi: np.ndarray,
                           weights: np.ndarray) -> float:
    weights = np.asarray(weights, dtype=np.complex128)
    weights = weights / np.linalg.norm(weights)
    combined = np.einsum("m,mtpc->tpc", weights, fields)
    power = np.sum(np.abs(combined)**2, axis=-1)
    power /= power.max()
    main = theta <= 20
    transition = (theta > 20) & (theta < 40)
    outside = theta >= 40
    target = np.zeros_like(theta)
    target[main] = 1
    target[transition] = 0.5 * (1 + np.cos(np.pi * (theta[transition] - 20) / 20))
    co = (combined[..., 0] * np.sin(np.deg2rad(phi))[None, :] +
          combined[..., 1] * np.cos(np.deg2rad(phi))[None, :])
    cross = (combined[..., 0] * np.cos(np.deg2rad(phi))[None, :] -
             combined[..., 1] * np.sin(np.deg2rad(phi))[None, :])
    cross_power = np.abs(cross)**2 / max(float(np.abs(co).max()**2), 1e-30)
    return float(4 * np.mean((power[main] - 1)**2) +
                 2 * np.mean((power[transition] - target[transition, None]**2)**2) +
                 12 * np.mean(power[outside]**2) +
                 10 * np.mean(cross_power[main]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("basis", type=Path)
    parser.add_argument("s_matrix", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--intrinsic", action="store_true",
                        help="Use intrinsic fields without the 50-ohm S-matrix proxy")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    with np.load(args.basis) as archive:
        data = {name: archive[name] for name in archive.files}
    s = None if args.intrinsic else load_s_matrix(args.s_matrix)
    theta = data["theta_deg"][::2]
    phi = data["phi_deg"][::2]
    all_fields = np.stack((data["e_theta"][:, ::2, ::2],
                           data["e_phi"][:, ::2, ::2]), axis=-1)
    rows = []
    for mode in range(2, 13):
        fields = all_fields[[0, mode - 1]]
        seed_results = []
        for seed in range(3):
            result = differential_evolution(
                lambda x: objective(fields, theta, phi, x[0], x[1]),
                bounds=[(0, 2.5), (-np.pi, np.pi)], seed=seed,
                maxiter=60, popsize=10, polish=True, tol=1e-8)
            seed_results.append(result)
        best = min(seed_results, key=lambda item: item.fun)
        weights = np.zeros(12, dtype=np.complex128)
        weights[0] = 1
        weights[mode - 1] = best.x[0] * np.exp(1j * best.x[1])
        metrics, _ = evaluate(data, s, weights)
        rows.append({
            "port_mode": mode,
            "coarse_objective": float(best.fun),
            "ratio": float(best.x[0]),
            "phase_deg": float(np.rad2deg(best.x[1])),
            "three_seed_evaluations": int(sum(run.nfev for run in seed_results)),
            "three_seed_best_objectives": "|".join(f"{run.fun:.9g}" for run in seed_results),
            **metrics,
        })
        print(f"mode {mode}: objective={best.fun:.4f}, "
              f"disk ripple={metrics['main_disk_ripple_db']:.3f} dB, "
              f"outside={metrics['outside_disk_db']:.3f} dB", flush=True)
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "two_mode_2d_scan.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "scan_summary.json").write_text(
        json.dumps({"status": "EXPLORATORY_FULL_AZIMUTH_TWO_MODE_SCAN",
                    "geometry_mm": [60, 20, 60],
                    "fixed_port_mode": 1,
                    "candidate_port_modes": list(range(2, 13)),
                    "seeds": [0, 1, 2],
                    "search_grid": {"theta_step_deg": 1, "phi_step_deg": 10},
                    "evaluation_grid": {"theta_step_deg": 0.5, "phi_step_deg": 5},
                    "objective": "2D extension of MATLAB E/H weighted power objective",
                    "source_reference": ("intrinsic_modal" if args.intrinsic else
                                         "50_ohm_postprocessed"),
                    "power_proxy_warning": ("Use native AcceptedPower for intrinsic basis."
                                            if args.intrinsic else
                                            "50-ohm-renormalized S only; native AcceptedPower required.")},
                   indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
