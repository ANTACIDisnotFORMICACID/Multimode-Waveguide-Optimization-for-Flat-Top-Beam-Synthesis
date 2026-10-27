"""Synthesize E/H cuts from two native HFSS embedded far fields.

The two port modes are chosen by unique propagation-constant groups. This is
an HFSS-basis synthesis, not a validation of MATLAB ideal-aperture weights or
a statement about the unsampled azimuths.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution


def read_fields(path: Path, modes: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    data = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            mode = int(row["PortMode"])
            if mode not in modes:
                continue
            plane = row["Plane"]
            theta = float(row["ThetaDeg"])
            e_theta = complex(float(row["EThetaReal"]), float(row["EThetaImag"]))
            e_phi = complex(float(row["EPhiReal"]), float(row["EPhiImag"]))
            data.setdefault((mode, plane), []).append((theta, e_theta, e_phi))
    if set(data) != {(mode, plane) for mode in modes for plane in ("E", "H")}:
        raise ValueError("Expected both E/H cuts for each selected mode")
    theta = np.array([sample[0] for sample in data[modes[0], "E"]])
    if len(theta) != 361 or not np.allclose(theta, np.arange(-90, 90.5, 0.5)):
        raise ValueError("Expected a signed 0.5-degree angular grid")
    fields = np.empty((2, len(theta), 2, 2), dtype=np.complex128)
    for m_idx, mode in enumerate(modes):
        for p_idx, plane in enumerate(("E", "H")):
            samples = data[mode, plane]
            if len(samples) != len(theta) or not np.allclose(
                    [sample[0] for sample in samples], theta):
                raise ValueError("All mode/plane angular grids must agree")
            fields[m_idx, :, p_idx, 0] = [sample[1] for sample in samples]
            fields[m_idx, :, p_idx, 1] = [sample[2] for sample in samples]
    return theta, fields


def evaluate(theta: np.ndarray, fields: np.ndarray, ratio: float,
             phase: float) -> tuple[float, np.ndarray, np.ndarray]:
    weights = np.array([1.0, ratio * np.exp(1j * phase)]) / math.sqrt(1 + ratio**2)
    combined = np.einsum("m,mtpc->tpc", weights, fields)
    power = np.sum(np.abs(combined)**2, axis=2)
    power /= power.max()
    co = np.column_stack((combined[:, 0, 0], combined[:, 1, 1]))
    cross = np.column_stack((-combined[:, 0, 1], combined[:, 1, 0]))
    cross_power = np.abs(cross)**2 / max(float(np.max(np.abs(co)**2)), 1e-30)
    absolute = np.abs(theta)
    main = absolute <= 20
    transition = (absolute > 20) & (absolute < 40)
    side = absolute >= 40
    target = np.zeros_like(theta)
    target[main] = 1
    target[transition] = 0.5 * (1 + np.cos(np.pi * (absolute[transition] - 20) / 20))
    target_power = target[:, None]**2
    objective = (4 * np.mean((power[main] - target_power[main])**2) +
                 2 * np.mean((power[transition] - target_power[transition])**2) +
                 12 * np.mean(power[side]**2) +
                 10 * np.mean(cross_power[main]))
    return float(objective), power, cross_power


def cut_metrics(theta: np.ndarray, power: np.ndarray,
                cross_power: np.ndarray) -> list[dict]:
    rows = []
    for idx, plane in enumerate(("E", "H")):
        normalized = power[:, idx] / power[:, idx].max()
        db = 10 * np.log10(np.maximum(normalized, 1e-12))
        main = np.abs(theta) <= 20
        outside = np.abs(theta) >= 40
        peak = int(np.argmax(normalized))
        left = np.flatnonzero(db[:peak] <= -3)
        right = np.flatnonzero(db[peak + 1:] <= -3)
        hpbw = math.nan
        if len(left) and len(right):
            a = int(left[-1])
            b = int(right[0] + peak + 1)
            l = np.interp(-3, db[a:a + 2], theta[a:a + 2])
            r = np.interp(-3, db[b - 1:b + 1][::-1], theta[b - 1:b + 1][::-1])
            hpbw = float(r - l)
        rows.append({"Plane": plane, "PeakDeg": float(theta[peak]),
                     "HpbwDeg": hpbw,
                     "MainRippleDb": float(db[main].max() - db[main].min()),
                     "OutsideMaxDb": float(db[outside].max()),
                     "MainCrossDb": float(10 * np.log10(max(
                         float(cross_power[main, idx].max()), 1e-12)))})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("embedded_cuts", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    theta, fields = read_fields(args.embedded_cuts, (1, 8))
    runs = []
    for seed in range(10):
        result = differential_evolution(
            lambda x: evaluate(theta, fields, float(x[0]), float(x[1]))[0],
            bounds=[(0, 2.5), (-np.pi, np.pi)], seed=seed,
            maxiter=80, popsize=12, polish=True, tol=1e-9)
        runs.append({"Seed": seed, "Objective": float(result.fun),
                     "Ratio": float(result.x[0]), "PhaseDeg": float(np.rad2deg(result.x[1])),
                     "Evaluations": int(result.nfev), "Converged": bool(result.success)})
    best = min(runs, key=lambda row: row["Objective"])
    baseline_obj, baseline_power, baseline_cross = evaluate(theta, fields, 0, 0)
    optimum_obj, optimum_power, optimum_cross = evaluate(
        theta, fields, best["Ratio"], np.deg2rad(best["PhaseDeg"]))
    metrics = []
    for design, objective, power, cross in (
            ("TE10 port 1", baseline_obj, baseline_power, baseline_cross),
            ("TE10+TE30 ports 1+8", optimum_obj, optimum_power, optimum_cross)):
        for row in cut_metrics(theta, power, cross):
            metrics.append({"Design": design, "Objective": objective, **row})
    args.output_dir.mkdir(parents=True)
    for name, rows in (("optimization_runs.csv", runs), ("cut_metrics.csv", metrics)):
        with (args.output_dir / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    with (args.output_dir / "patterns.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Plane", "ThetaDeg", "TE10Db", "TwoModeDb"])
        for idx, plane in enumerate(("E", "H")):
            for angle, p0, p1 in zip(theta, baseline_power[:, idx], optimum_power[:, idx]):
                writer.writerow([plane, angle, 10 * np.log10(max(p0 / baseline_power[:, idx].max(), 1e-12)),
                                 10 * np.log10(max(p1 / optimum_power[:, idx].max(), 1e-12))])
    summary = {"status": "HFSS_EMBEDDED_TWO_MODE_EH_SYNTHESIS",
               "port_modes": [1, 8], "analytic_groups_by_beta": ["TE10", "TE30"],
               "half_width_deg": 20, "transition_deg": 20,
               "two_plane_only": True, "independent_full_wave_resolve": False,
               "best": best, "objective_baseline": baseline_obj,
               "objective_optimum": optimum_obj}
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "metrics": metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
