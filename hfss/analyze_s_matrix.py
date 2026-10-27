"""Calculate reproducible reciprocity/passivity diagnostics for native HFSS S."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


def read_s_matrix(path: Path, port_modes: int) -> np.ndarray:
    matrix = np.full((port_modes, port_modes), np.nan + 1j * np.nan)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != port_modes**2:
        raise ValueError("Incomplete native S matrix")
    seen = set()
    for row in rows:
        receive = int(row["ReceivePortMode"]) - 1
        source = int(row["SourcePortMode"]) - 1
        if not (0 <= receive < port_modes and 0 <= source < port_modes):
            raise ValueError("Port-mode index outside matrix")
        if (receive, source) in seen:
            raise ValueError("Repeated S-matrix entry")
        seen.add((receive, source))
        if row["FreqUnit"] != "GHz" or not math.isclose(
                float(row["FreqValue"]), 30.0, rel_tol=1e-9):
            raise ValueError("Unexpected frequency in native S matrix")
        matrix[receive, source] = complex(float(row["SReal"]), float(row["SImag"]))
    if not np.isfinite(matrix).all():
        raise ValueError("Nonfinite native S matrix")
    return matrix


def diagnostics(matrix: np.ndarray) -> tuple[dict, list[dict]]:
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("S matrix must be square")
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    diagonal = np.abs(np.diag(matrix))
    rows = [{"PortMode": index, "SelfReflectionMagnitude": float(value),
             "SelfReflectionDb": float(20 * np.log10(max(value, 1e-300)))}
            for index, value in enumerate(diagonal, start=1)]
    summary = {"status": "NATIVE_S_MATRIX_DIAGNOSTICS",
               "port_modes": len(matrix),
               "max_reciprocity_error": float(np.max(np.abs(matrix - matrix.T))),
               "max_singular_value": float(singular_values[0]),
               "singular_values": [float(value) for value in singular_values],
               "interpretation": "50-ohm-renormalized S; not a modal field identity test"}
    return summary, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("s_matrix", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--port-modes", type=int, choices=(10, 12), default=12)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    summary, rows = diagnostics(read_s_matrix(args.s_matrix, args.port_modes))
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "s_matrix_diagnostics.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "port_self_reflection.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
