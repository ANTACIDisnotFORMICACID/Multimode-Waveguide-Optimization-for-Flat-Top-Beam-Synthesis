"""Plot HFSS embedded-field two-mode E/H synthesis without hiding tradeoffs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns_csv", type=Path)
    parser.add_argument("output_stem", type=Path)
    args = parser.parse_args()

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with args.patterns_csv.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4), sharey=True,
                             constrained_layout=True)
    for ax, plane, label in zip(axes, ("E", "H"), ("a", "b")):
        part = [row for row in rows if row["Plane"] == plane]
        if len(part) != 361:
            raise ValueError("Expected 361 signed samples per plane")
        x = [float(row["ThetaDeg"]) for row in part]
        baseline = [max(-40, float(row["TE10Db"])) for row in part]
        combined = [max(-40, float(row["TwoModeDb"])) for row in part]
        ax.plot(x, baseline, color="#1f4e79", linewidth=1.8, label="TE10")
        ax.plot(x, combined, color="#d55e00", linewidth=1.8,
                linestyle="--", label="TE10 + TE30")
        for edge in (-40, -20, 20, 40):
            ax.axvline(edge, color="#777777", linewidth=0.8, linestyle=":")
        ax.set(xlabel=r"Signed angle $\theta$ (deg)",
               title=f"({label}) {plane}-plane", xlim=(-90, 90), ylim=(-40, 1))
        ax.set_xticks(range(-90, 91, 30))
        ax.grid(alpha=0.2)
        ax.legend(frameon=False, fontsize=8)
    axes[0].set_ylabel("Normalized power (dB)")
    stem = args.output_stem
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    fig.savefig(stem.with_suffix(".pdf"))
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
