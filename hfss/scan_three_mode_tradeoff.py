"""Explore the two-dimensional ripple/outside tradeoff on intrinsic HFSS fields.

This is an exploratory fixed-port scan. It does not identify port eigenmodes or
claim a global Pareto frontier. A separate dense angular grid evaluates every
candidate after coarse-grid optimization.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import differential_evolution

from analyze_full_azimuth import evaluate
from optimize_three_mode_2d import BOUNDS, decode


PORTS = (1, 5, 8)
OUTSIDE_WEIGHTS = (0.0, 0.1, 0.3, 1.0, 3.0)


def component_metrics(fields: np.ndarray, theta: np.ndarray,
                      phi: np.ndarray, x: np.ndarray) -> tuple[float, float, float]:
    w = decode(x)[np.array(PORTS) - 1]
    combined = np.einsum("m,mtpc->tpc", w, fields)
    power = np.sum(np.abs(combined)**2, axis=-1)
    peak = max(float(power.max()), 1e-30)
    main = theta <= 20
    outside = theta >= 40
    main_power = power[main]
    ripple_db = 10 * np.log10(float(main_power.max() / max(main_power.min(), 1e-30)))
    outside_linear = float(power[outside].max() / peak)
    angle = np.deg2rad(phi)
    co = combined[..., 0] * np.sin(angle) + combined[..., 1] * np.cos(angle)
    cross = combined[..., 0] * np.cos(angle) - combined[..., 1] * np.sin(angle)
    cross_linear = float(np.abs(cross[main]).max()**2 /
                         max(np.abs(co).max()**2, 1e-30))
    return ripple_db, outside_linear, cross_linear


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("basis", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--maxiter", type=int, default=40)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    if args.seeds < 1 or args.maxiter < 1:
        parser.error("seeds and maxiter must be positive")
    with np.load(args.basis) as archive:
        data = {key: archive[key] for key in archive.files}
    if data["e_theta"].shape != (12, 181, 72):
        raise ValueError("Expected the verified 12-mode intrinsic full-azimuth basis")
    fields = np.stack((data["e_theta"][[0, 4, 7], ::2, ::2],
                       data["e_phi"][[0, 4, 7], ::2, ::2]), axis=-1)
    theta, phi = data["theta_deg"][::2], data["phi_deg"][::2]
    rows = []
    for outside_weight in OUTSIDE_WEIGHTS:
        for seed in range(args.seeds):
            def objective(x: np.ndarray) -> float:
                ripple, outside, cross = component_metrics(fields, theta, phi, x)
                return ripple / 10 + outside_weight * 10 * outside + 2 * cross

            result = differential_evolution(
                objective, BOUNDS, seed=seed, popsize=8,
                maxiter=args.maxiter, polish=False, tol=1e-8)
            dense, _ = evaluate(data, None, decode(result.x))
            rows.append({"outside_weight": outside_weight, "seed": seed,
                         "coarse_objective": float(result.fun),
                         "evaluations": int(result.nfev),
                         "main_disk_ripple_db": dense["main_disk_ripple_db"],
                         "outside_disk_db": dense["outside_disk_db"],
                         "main_cross_db": dense["main_cross_db"],
                         "peak_theta_deg": dense["peak_theta_deg"],
                         "peak_phi_deg": dense["peak_phi_deg"],
                         "port_5_amplitude": float(abs(decode(result.x)[4])),
                         "port_5_phase_deg": float(np.rad2deg(np.angle(decode(result.x)[4]))),
                         "port_8_amplitude": float(abs(decode(result.x)[7])),
                         "port_8_phase_deg": float(np.rad2deg(np.angle(decode(result.x)[7]))),
                         })
        print(f"outside weight {outside_weight:g}: {args.seeds} seeds complete", flush=True)
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "tradeoff_runs.csv").open("w", newline="",
                                                     encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    fig, ax = plt.subplots(figsize=(6.4, 4.8), layout="constrained")
    markers = ("o", "s", "^", "D", "P")
    colors = ("#222222", "#1372A3", "#0A9673", "#DB6A24", "#9D3B8F")
    for weight, marker, color in zip(OUTSIDE_WEIGHTS, markers, colors):
        selected = [row for row in rows if row["outside_weight"] == weight]
        ax.scatter([row["main_disk_ripple_db"] for row in selected],
                   [row["outside_disk_db"] for row in selected],
                   marker=marker, color=color, s=46, label=f"weight {weight:g}")
    ax.set_xlabel("Main-disk ripple (dB)")
    ax.set_ylabel("Maximum outside level (dB)")
    ax.grid(alpha=0.2)
    ax.legend(title="Outside term", fontsize=8)
    fig.savefig(args.output_dir / "three_mode_tradeoff.png", dpi=300)
    fig.savefig(args.output_dir / "three_mode_tradeoff.pdf")
    plt.close(fig)
    (args.output_dir / "receipt.json").write_text(json.dumps({
        "status": "EXPLORATORY_FIXED_THREE_PORT_TRADEOFF",
        "basis": str(args.basis), "source_reference": "intrinsic_modal",
        "ports": PORTS, "outside_weights": OUTSIDE_WEIGHTS,
        "seeds_per_weight": args.seeds, "maxiter": args.maxiter,
        "coarse_grid": "1 deg theta x 10 deg phi",
        "evaluation_grid": "0.5 deg theta x 5 deg phi",
        "objective": "ripple_db/10 + weight*10*outside_linear + 2*cross_linear",
        "global_optimality_claim": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
