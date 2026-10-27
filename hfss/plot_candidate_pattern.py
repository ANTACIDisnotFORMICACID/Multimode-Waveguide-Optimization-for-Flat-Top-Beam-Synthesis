"""Plot the full signed E/H cuts of an ideal-horn/HFSS candidate comparison."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("overlay_csv", type=Path)
    parser.add_argument("output_stem", type=Path)
    parser.add_argument("--phase-overlay-csv", type=Path)
    args = parser.parse_args()

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with args.overlay_csv.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    phase_rows = None
    if args.phase_overlay_csv:
        with args.phase_overlay_csv.open(newline="", encoding="utf-8") as stream:
            phase_rows = list(csv.DictReader(stream))
        if len(phase_rows) != len(rows):
            raise ValueError("Quadratic-phase overlay has a different angular grid")
    if len(rows) != 722:
        raise ValueError("Expected 361 samples for each E/H cut")
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4), sharey=True,
                             constrained_layout=True)
    for ax, plane, label in zip(axes, ("E", "H"), ("a", "b")):
        subset = [row for row in rows if row["Plane"] == plane]
        theta = [float(row["ThetaDeg"]) for row in subset]
        ideal = [max(-40, float(row["ReferenceDb"])) for row in subset]
        hfss = [max(-40, float(row["HfssDb"])) for row in subset]
        ax.plot(theta, ideal, color="#1f4e79", linewidth=1.8,
                label="Ideal aperture")
        if phase_rows is not None:
            phase_subset = [row for row in phase_rows if row["Plane"] == plane]
            if [float(row["ThetaDeg"]) for row in phase_subset] != theta:
                raise ValueError("Quadratic-phase overlay has a different angular grid")
            phase = [max(-40, float(row["ReferenceDb"])) for row in phase_subset]
            ax.plot(theta, phase, color="#444444", linewidth=1.5,
                    linestyle="-.", label="Quadratic phase")
        ax.plot(theta, hfss, color="#d55e00", linewidth=1.6,
                linestyle="--", label="HFSS port 1")
        ax.set(xlabel=r"Signed angle $\theta$ (deg)", title=f"({label}) {plane}-plane",
               xlim=(-90, 90), ylim=(-40, 1))
        ax.set_xticks(range(-90, 91, 30))
        ax.grid(alpha=0.22)
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
