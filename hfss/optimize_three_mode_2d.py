"""Compare local and hybrid three-port optimization on native HFSS fields."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.optimize import differential_evolution, minimize

from analyze_full_azimuth import evaluate, load_s_matrix
from scan_two_mode_2d import objective_from_weights


PORTS = (1, 5, 8)
BOUNDS = [(0, 2.5), (0, 2.5), (-np.pi, np.pi), (-np.pi, np.pi)]


class EvaluationBudgetExhausted(Exception):
    pass


def decode(x: np.ndarray) -> np.ndarray:
    w = np.zeros(12, dtype=np.complex128)
    w[0] = 1
    w[4] = x[0] * np.exp(1j * x[2])
    w[7] = x[1] * np.exp(1j * x[3])
    return w / np.linalg.norm(w)


def least_squares_start(data: dict) -> np.ndarray:
    theta = data["theta_deg"][::2]
    phi = np.deg2rad(data["phi_deg"][::2])
    et = data["e_theta"][[0, 4, 7], ::2, ::2]
    ep = data["e_phi"][[0, 4, 7], ::2, ::2]
    co = et * np.sin(phi)[None, None, :] + ep * np.cos(phi)[None, None, :]
    target = np.zeros_like(theta)
    target[theta <= 20] = 1
    transition = (theta > 20) & (theta < 40)
    target[transition] = 0.5 * (1 + np.cos(np.pi * (theta[transition] - 20) / 20))
    first = co[0]
    desired = target[:, None] * np.abs(first).max() * np.exp(1j * np.angle(first))
    desired = np.broadcast_to(desired, first.shape)
    w = np.linalg.lstsq(co.reshape(3, -1).T, desired.ravel(), rcond=None)[0]
    if abs(w[0]) < 1e-12:
        raise ValueError("Least-squares TE10 reference amplitude vanished")
    ratios = w[1:] / w[0]
    return np.array([np.clip(abs(z), 0, 2.5) for z in ratios] +
                    [np.angle(z) for z in ratios], dtype=float)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("basis", type=Path)
    parser.add_argument("s_matrix", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--intrinsic", action="store_true",
                        help="Use intrinsic fields without a 50-ohm S-matrix proxy")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    with np.load(args.basis) as archive:
        data = {key: archive[key] for key in archive.files}
    s = None if args.intrinsic else load_s_matrix(args.s_matrix)
    theta = data["theta_deg"][::2]
    phi = data["phi_deg"][::2]
    fields = np.stack((data["e_theta"][[0, 4, 7], ::2, ::2],
                       data["e_phi"][[0, 4, 7], ::2, ::2]), axis=-1)

    def fun(x: np.ndarray) -> float:
        w = np.array([1, x[0] * np.exp(1j * x[2]),
                       x[1] * np.exp(1j * x[3])])
        return objective_from_weights(fields, theta, phi, w)

    rows = []
    solutions = []
    ls_start = least_squares_start(data)
    local = minimize(fun, ls_start, method="L-BFGS-B", bounds=BOUNDS,
                     options={"maxfun": 3000, "ftol": 1e-11})
    rows.append({"method": "complex-LS + local", "seed": -1,
                 "coarse_objective": float(local.fun), "evaluations": int(local.nfev),
                 "converged": bool(local.success), **evaluate(data, s, decode(local.x))[0]})
    solutions.append(("complex-LS + local", -1, local.x, local.fun))
    print(f"LS+local: {local.fun:.5f}, evaluations={local.nfev}", flush=True)

    for seed in range(10):
        de = differential_evolution(fun, BOUNDS, seed=seed,
                                    maxiter=55, popsize=12,
                                    polish=False, tol=1e-9)
        remaining = 3000 - de.nfev
        state = {"calls": 0, "x": de.x.copy(), "fun": float(de.fun)}

        def limited_fun(x: np.ndarray) -> float:
            if state["calls"] >= remaining:
                raise EvaluationBudgetExhausted
            value = fun(x)
            state["calls"] += 1
            if value < state["fun"]:
                state["x"] = x.copy()
                state["fun"] = float(value)
            return value

        local_converged = False
        try:
            result = minimize(limited_fun, de.x, method="L-BFGS-B",
                              bounds=BOUNDS, options={"maxfun": remaining, "ftol": 1e-11})
            local_converged = bool(result.success)
        except EvaluationBudgetExhausted:
            pass
        refined = SimpleNamespace(x=state["x"], fun=state["fun"],
                                  nfev=state["calls"], success=local_converged)
        for method, result, evaluations in (
                ("differential evolution", de, de.nfev),
                ("DE + local", refined, de.nfev + refined.nfev)):
            rows.append({"method": method, "seed": seed,
                         "coarse_objective": float(result.fun),
                         "evaluations": int(evaluations),
                         "converged": bool(result.success),
                         **evaluate(data, s, decode(result.x))[0]})
            solutions.append((method, seed, result.x, result.fun))
        print(f"seed {seed}: DE={de.fun:.5f}, hybrid={refined.fun:.5f}, "
              f"calls={de.nfev + refined.nfev}", flush=True)
    selected = min(solutions, key=lambda row: row[3])
    selected_weights = decode(selected[2])
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "optimization_runs.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (args.output_dir / "selected_weights.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["PortMode", "Amplitude", "PhaseDeg"])
        for i, w in enumerate(selected_weights, 1):
            if abs(w) >= 1e-6:
                writer.writerow([i, abs(w), np.rad2deg(np.angle(w))])
    metrics, _ = evaluate(data, s, selected_weights)
    (args.output_dir / "summary.json").write_text(
        json.dumps({"status": "EXPLORATORY_THREE_PORT_FULL_AZIMUTH_OPTIMIZATION",
                    "ports": PORTS,
                    "same_geometry_full_wave_basis": True,
                    "independent_full_wave_resolve": False,
                    "coarse_grid": {"theta_step_deg": 1, "phi_step_deg": 10},
                    "dense_evaluation_grid": {"theta_step_deg": 0.5, "phi_step_deg": 5},
                    "budget_per_seed": 3000,
                    "selected_method": selected[0],
                    "selected_seed": selected[1],
                    "selected_coarse_objective": float(selected[3]),
                    "selected_dense_metrics": metrics,
                    "source_reference": ("intrinsic_modal" if args.intrinsic else
                                         "50_ohm_postprocessed"),
                    "power_proxy_warning": ("Use native AcceptedPower for intrinsic source settings."
                                            if args.intrinsic else
                                            "50-ohm-renormalized S; native AcceptedPower required.")},
                   indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
