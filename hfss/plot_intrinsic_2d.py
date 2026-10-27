"""Plot intrinsic-port HFSS 2D patterns for one-, two-, and three-mode cases."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze_full_azimuth import evaluate
from verify_composite_sources import read_weights


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("basis", type=Path)
    parser.add_argument("two_mode_scan", type=Path)
    parser.add_argument("three_mode_weights", type=Path)
    parser.add_argument("output_stem", type=Path)
    args = parser.parse_args()
    with np.load(args.basis) as archive:
        data = {key: archive[key] for key in archive.files}
    with args.two_mode_scan.open(newline="", encoding="utf-8") as stream:
        row = next(item for item in csv.DictReader(stream)
                   if int(item["port_mode"]) == 8)
    one = np.zeros(12, complex)
    one[0] = 1
    two = one.copy()
    two[7] = float(row["ratio"]) * np.exp(1j * np.deg2rad(float(row["phase_deg"])))
    three = read_weights(args.three_mode_weights)
    cases = [("(a) Port 1", one),
             ("(b) Ports 1 + 8", two),
             ("(c) Ports 1 + 5 + 8", three)]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.3),
                             subplot_kw={"projection": "polar"},
                             layout="constrained")
    angle = np.deg2rad(data["phi_deg"])
    radius = data["theta_deg"]
    for ax, (label, weights) in zip(axes, cases):
        metrics, power_db = evaluate(data, None, weights)
        img = ax.pcolormesh(angle, radius, np.maximum(power_db, -40),
                            shading="nearest", cmap="viridis",
                            vmin=-40, vmax=0, rasterized=True)
        ax.set_theta_zero_location("E")
        ax.set_theta_direction(-1)
        ax.set_ylim(0, 90)
        ax.set_rticks([20, 40, 60, 80])
        ax.set_rlabel_position(70)
        ax.tick_params(labelsize=8)
        for threshold, style in ((20, "--"), (40, ":")):
            ax.plot(np.linspace(0, 2 * np.pi, 361),
                    np.full(361, threshold), color="white",
                    linestyle=style, linewidth=1.2)
        ax.set_title(label, fontsize=12, pad=16)
        ax.text(0.5, -0.13,
                f"Ripple {metrics['main_disk_ripple_db']:.2f} dB  |  "
                f"Outside {metrics['outside_disk_db']:.2f} dB",
                transform=ax.transAxes, ha="center", va="top", fontsize=9)
    fig.colorbar(img, ax=axes, shrink=0.71, pad=0.035,
                 label="Normalized radiated power (dB)")
    args.output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_stem.with_suffix(".png"), dpi=300)
    fig.savefig(args.output_stem.with_suffix(".pdf"))
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
