"""Compare near-port total E grids with analytic transverse mode templates.

This is a diagnostic proxy, NOT a port-eigenfield identification. HFSS's
exported 3D field contains incident and reflected waves; a high correlation
only says that one analytic spatial template dominates at the sampled plane.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


def load_grid(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    samples = np.loadtxt(path, skiprows=2)
    if samples.ndim != 2 or samples.shape[1] != 9 or len(samples) < 25:
        raise ValueError(f"Expected a nine-column complex vector grid: {path}")
    if not np.isfinite(samples).all():
        raise ValueError(f"Nonfinite field samples: {path}")
    x, y = samples[:, 0], samples[:, 1]
    if len(np.unique(x)) * len(np.unique(y)) != len(samples):
        raise ValueError(f"Incomplete or repeated rectangular grid: {path}")
    ex = samples[:, 3] + 1j * samples[:, 4]
    ey = samples[:, 5] + 1j * samples[:, 6]
    return x, y, ex, ey


def transverse_template(
    family: str, m: int, n: int, x_mm: np.ndarray, y_mm: np.ndarray,
    width_mm: float = 20.0, height_mm: float = 10.0,
) -> np.ndarray:
    """Unscaled transverse TE/TM E field, consistent with wg.mode_fields."""
    xs = x_mm + width_mm / 2.0
    ys = y_mm + height_mm / 2.0
    kx = m * math.pi / width_mm
    ky = n * math.pi / height_mm
    base_x = np.cos(kx * xs) * np.sin(ky * ys)
    base_y = np.sin(kx * xs) * np.cos(ky * ys)
    if family == "TE":
        ex, ey = ky * base_x, -kx * base_y
    elif family == "TM":
        ex, ey = kx * base_x, ky * base_y
    else:
        raise ValueError(f"Unknown mode family: {family}")
    return np.concatenate((ex, ey)).astype(np.complex128)


def normalized_correlation(reference: np.ndarray, actual: np.ndarray) -> float:
    denominator = np.linalg.norm(reference) * np.linalg.norm(actual)
    if denominator == 0:
        raise ValueError("Zero-norm mode template or measured field")
    return float(abs(np.vdot(reference, actual)) / denominator)


def analyze(input_dir: Path, catalog: Path, output_dir: Path) -> list[dict]:
    with catalog.open(newline="", encoding="utf-8") as stream:
        modes = [row for row in csv.DictReader(stream) if row["Status"] == "propagating"]
    if not modes:
        raise ValueError("No propagating modes in catalog")
    files = sorted(input_dir.glob("total_E_port_mode_*.fld"),
                   key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    if not files:
        raise ValueError("No total-field grid files")
    output_dir.mkdir(parents=True, exist_ok=False)
    all_rows = []
    summaries = []
    shared_xy = None
    for path in files:
        port_mode = int(path.stem.rsplit("_", 1)[1])
        x, y, ex, ey = load_grid(path)
        if shared_xy is None:
            shared_xy = (x, y)
        elif not (np.array_equal(x, shared_xy[0]) and np.array_equal(y, shared_xy[1])):
            raise ValueError("Inconsistent sampling grids across HFSS port modes")
        measured = np.concatenate((ex, ey))
        for mode in modes:
            template = transverse_template(mode["Family"], int(mode["m"]),
                                           int(mode["n"]), x, y)
            all_rows.append({"PortMode": port_mode, "Template": mode["Name"],
                             "Correlation": normalized_correlation(template, measured)})
        ranked = sorted((r for r in all_rows if r["PortMode"] == port_mode),
                        key=lambda r: r["Correlation"], reverse=True)
        best, second = ranked[:2]
        summaries.append({"PortMode": port_mode, "DominantTemplate": best["Template"],
                          "DominantCorrelation": best["Correlation"],
                          "NextTemplate": second["Template"],
                          "NextCorrelation": second["Correlation"],
                          "Interpretation": "TOTAL_FIELD_PROXY_ONLY"})
    for name, rows, columns in (
        ("template_correlations.csv", all_rows,
         ["PortMode", "Template", "Correlation"]),
        ("dominant_templates.csv", summaries,
         ["PortMode", "DominantTemplate", "DominantCorrelation",
          "NextTemplate", "NextCorrelation", "Interpretation"]),
    ):
        with (output_dir / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    (output_dir / "analysis_receipt.json").write_text(json.dumps({
        "status": "TOTAL_FIELD_TEMPLATE_PROXY",
        "input_dir": str(input_dir.resolve()),
        "catalog": str(catalog.resolve()),
        "samples_per_grid": len(shared_xy[0]),
        "port_modes": [item["PortMode"] for item in summaries],
        "note": "3D total fields contain reflected waves; these are not port eigenfields.",
    }, indent=2) + "\n", encoding="utf-8")
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    for item in analyze(args.input_dir, args.catalog, args.output_dir):
        print(f"{item['PortMode']:2d} {item['DominantTemplate']:4s} "
              f"{item['DominantCorrelation']:.4f}  "
              f"next {item['NextTemplate']:4s} {item['NextCorrelation']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
