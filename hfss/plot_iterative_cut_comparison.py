"""Plot E/H cuts for the same fixed excitations on the 12/15-pass meshes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from compare_iterative_cuts import (PHIS, THETA, normalized_db,
                                    read_new_cuts, read_old_cuts)
from verify_composite_sources import read_weights


def signed_cut(db: np.ndarray, positive_phi: int, negative_phi: int):
    positive = db[PHIS.index(positive_phi)]
    negative = db[PHIS.index(negative_phi)]
    angle = np.concatenate((-THETA[:0:-1], THETA))
    values = np.concatenate((negative[:0:-1], positive))
    return angle, values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_basis", type=Path)
    parser.add_argument("new_cuts", type=Path)
    parser.add_argument("weights", type=Path)
    parser.add_argument("output_stem", type=Path)
    parser.add_argument("--fixed-only", action="store_true",
                        help="Plot only the fixed three-mode E/H cuts")
    args = parser.parse_args()
    old = read_old_cuts(args.baseline_basis)
    new = read_new_cuts(args.new_cuts)
    single = np.zeros(12, dtype=np.complex128)
    single[0] = 1.0
    cases = (("Port 1", single),
             ("Fixed ports 1, 5, 8", read_weights(args.weights)))
    if args.fixed_only:
        cases = cases[1:]
    planes = (("E plane", 90, 270), ("H plane", 0, 180))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.linewidth": 0.8, "pdf.fonttype": 42})
    figure, axes = plt.subplots(len(cases), 2,
                               figsize=(10.2, 3.5 if args.fixed_only else 6.1),
                               sharex=True, sharey=True, squeeze=False)
    for row, (name, weights) in enumerate(cases):
        old_db = normalized_db(np.tensordot(weights, old, axes=(0, 0)))
        new_db = normalized_db(np.tensordot(weights, new, axes=(0, 0)))
        for col, (plane, positive, negative) in enumerate(planes):
            axis = axes[row, col]
            axis.axvspan(-20, 20, color="#E8EEF5", zorder=0)
            old_angle, old_values = signed_cut(old_db, positive, negative)
            new_angle, new_values = signed_cut(new_db, positive, negative)
            axis.plot(old_angle, old_values, color="#232323", linewidth=1.4,
                      linestyle="--", label="12 passes")
            axis.plot(new_angle, new_values, color="#0072B2", linewidth=1.45,
                      label="15 passes")
            visible = (old_values > -20) | (new_values > -20)
            rmse = np.sqrt(np.mean((old_values[visible] - new_values[visible]) ** 2))
            axis.text(0.03, 0.06, "RMSE = {:.3f} dB".format(rmse),
                      transform=axis.transAxes, fontsize=8,
                      bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8})
            panel_label = (plane if args.fixed_only else "{} · {}".format(name, plane))
            axis.text(0.02, 0.96, "({}) {}".format(
                "abcd"[row * 2 + col], panel_label),
                transform=axis.transAxes, va="top", fontsize=9)
            axis.grid(True, color="#D8D8D8", linewidth=0.5)
            axis.set_xlim(-90, 90)
            axis.set_ylim(-40, 1)
            axis.set_xticks(np.arange(-90, 91, 30))
            axis.set_yticks(np.arange(-40, 1, 10))
            if row == len(cases) - 1:
                axis.set_xlabel(r"Signed angle $\theta$ (deg)")
            if col == 0:
                axis.set_ylabel("Normalized field (dB)")
    axes[0, 0].legend(loc="lower center", frameon=True, fontsize=8)
    figure.tight_layout()
    stem = args.output_stem.resolve()
    stem.parent.mkdir(parents=True, exist_ok=True)
    if stem.with_suffix(".png").exists() or stem.with_suffix(".pdf").exists():
        parser.error("Plot output already exists")
    figure.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    figure.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
