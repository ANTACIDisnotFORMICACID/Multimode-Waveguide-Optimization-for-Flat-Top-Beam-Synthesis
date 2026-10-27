"""Plot native Ports Only propagation constants against analytic mode groups."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison_csv", type=Path)
    parser.add_argument("output_stem", type=Path)
    args = parser.parse_args()

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with args.comparison_csv.open(newline="", encoding="utf-8") as stream:
        rows = sorted(csv.DictReader(stream), key=lambda row: int(row["PortMode"]))
    if len(rows) != 12 or [int(row["PortMode"]) for row in rows] != list(range(1, 13)):
        raise ValueError("Expected one sorted comparison row for each of 12 port modes")

    indices = [int(row["PortMode"]) for row in rows]
    analytic = [float(row["AnalyticBetaRadPerM"]) for row in rows]
    hfss = [float(row["HfssGammaImagPerM"]) for row in rows]
    errors = [float(row["RelativeBetaErrorPct"]) for row in rows]

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.5), constrained_layout=True)
    ax = axes[0]
    ax.plot(indices, analytic, "o-", color="#1f4e79", markersize=4,
            linewidth=1.6, label="Analytic mode group")
    ax.plot(indices, hfss, "x", color="#d55e00", markersize=6,
            markeredgewidth=1.3, label="HFSS Ports Only")
    ax.set(xlabel="HFSS port mode index", ylabel=r"Propagation constant $\beta$ (rad/m)",
           xlim=(0.5, 12.5), ylim=(0, 650))
    ax.set_xticks(indices)
    ax.grid(alpha=0.22)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.text(0.98, 0.97, "(a)", transform=ax.transAxes, va="top",
            ha="right", fontweight="bold")

    ax = axes[1]
    ax.bar(indices, errors, color=["#d55e00" if i >= 11 else "#1f4e79"
                                      for i in indices], width=0.68)
    ax.set(xlabel="HFSS port mode index", ylabel=r"Relative $\beta$ difference (%)",
           xlim=(0.5, 12.5), ylim=(0, 1.3))
    ax.set_xticks(indices)
    ax.grid(axis="y", alpha=0.22)
    ax.text(0.02, 0.97, "(b)", transform=ax.transAxes, va="top", fontweight="bold")
    ax.annotate("Near cutoff", xy=(11.5, max(errors[-2:])),
                xytext=(8.5, 1.1), fontsize=8,
                arrowprops={"arrowstyle": "->", "color": "#555555"})

    stem = args.output_stem
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    fig.savefig(stem.with_suffix(".pdf"))
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
