"""Audit existing modal weights on the verified HFSS full-azimuth basis."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_s_matrix(path: Path) -> np.ndarray:
    s = np.zeros((12, 12), dtype=np.complex128)
    seen = set()
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            receive, source = int(row["ReceivePortMode"]), int(row["SourcePortMode"])
            seen.add((receive, source))
            s[receive - 1, source - 1] = complex(float(row["SReal"]),
                                                 float(row["SImag"]))
    if len(seen) != 144:
        raise ValueError("Expected a complete 12x12 scattering matrix")
    return s


def evaluate(data: dict, s: np.ndarray | None, weights: np.ndarray) -> tuple[dict, np.ndarray]:
    weights = np.asarray(weights, dtype=np.complex128)
    weights = weights / np.linalg.norm(weights)
    e_theta = np.einsum("m,mtp->tp", weights, data["e_theta"])
    e_phi = np.einsum("m,mtp->tp", weights, data["e_phi"])
    power = np.abs(e_theta)**2 + np.abs(e_phi)**2
    peak = float(power.max())
    theta = data["theta_deg"]
    phi = data["phi_deg"]
    main = theta <= 20
    outside = theta >= 40
    co = e_theta * np.sin(np.deg2rad(phi))[None, :] + e_phi * np.cos(np.deg2rad(phi))[None, :]
    cross = e_theta * np.cos(np.deg2rad(phi))[None, :] - e_phi * np.sin(np.deg2rad(phi))[None, :]
    maximum = np.unravel_index(int(power.argmax()), power.shape)
    returned = float(np.linalg.norm(s @ weights)**2) if s is not None else None
    metrics = {
        "active_modes": int(np.count_nonzero(np.abs(weights) >= 1e-3)),
        "main_disk_ripple_db": float(10 * np.log10(power[main].max() / power[main].min())),
        "outside_disk_db": float(10 * np.log10(power[outside].max() / peak)),
        "boresight_relative_db": float(10 * np.log10(power[0, 0] / peak)),
        "peak_theta_deg": float(theta[maximum[0]]),
        "peak_phi_deg": float(phi[maximum[1]]),
        "main_cross_db": float(10 * np.log10(np.abs(cross[main]).max()**2 /
                                               np.abs(co).max()**2)),
        "returned_power_proxy": returned,
        "nonreturned_power_proxy": 1 - returned if returned is not None else None,
    }
    return metrics, 10 * np.log10(np.maximum(power / peak, 1e-12))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("basis", type=Path)
    parser.add_argument("s_matrix", type=Path)
    parser.add_argument("two_mode_summary", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--intrinsic", action="store_true",
                        help="Do not apply the 50-ohm-renormalized S matrix to an intrinsic field basis")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    with np.load(args.basis) as archive:
        data = {name: archive[name] for name in archive.files}
    if data["e_theta"].shape != (12, 181, 72):
        raise ValueError("Expected the verified 12-mode full-azimuth export")
    s = None if args.intrinsic else load_s_matrix(args.s_matrix)
    optimum = json.loads(args.two_mode_summary.read_text(encoding="utf-8"))["best"]
    weights = np.zeros((2, 12), dtype=np.complex128)
    weights[:, 0] = 1
    weights[1, 7] = optimum["Ratio"] * np.exp(1j * np.deg2rad(optimum["PhaseDeg"]))
    names = ["TE10 candidate (port 1)", "Ports 1 + 8"]
    rows = []
    maps = []
    for name, weight in zip(names, weights):
        metrics, map_db = evaluate(data, s, weight)
        rows.append({"design": name, **metrics})
        maps.append(map_db)
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "full_azimuth_metrics.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6),
                             subplot_kw={"projection": "polar"},
                             layout="constrained")
    phi_rad = np.deg2rad(data["phi_deg"])
    theta = data["theta_deg"]
    for ax, name, map_db in zip(axes, names, maps):
        artist = ax.pcolormesh(phi_rad, theta, np.maximum(map_db, -40),
                               shading="nearest", cmap="viridis", vmin=-40, vmax=0,
                               rasterized=True)
        ax.set_theta_zero_location("E")
        ax.set_theta_direction(-1)
        ax.set_ylim(0, 90)
        ax.set_rticks([20, 40, 60, 80])
        ax.set_rlabel_position(80)
        for radius, style in ((20, "--"), (40, ":")):
            ax.plot(np.linspace(0, 2 * np.pi, 361),
                    np.full(361, radius), color="white", linestyle=style, linewidth=1.3)
        ax.set_title(name, pad=18)
    fig.colorbar(artist, ax=axes, shrink=0.77, pad=0.07,
                 label="Normalized radiated power (dB)")
    fig.savefig(args.output_dir / "full_azimuth_comparison.png", dpi=300)
    fig.savefig(args.output_dir / "full_azimuth_comparison.pdf")
    plt.close(fig)
    (args.output_dir / "analysis.json").write_text(
        json.dumps({"basis": str(args.basis), "rows": rows,
                    "power_proxy_note": ("Unavailable for intrinsic basis; use native AcceptedPower."
                                         if args.intrinsic else
                                         "Computed from 50-ohm-renormalized S; verify against native AcceptedPower.")},
                   indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
