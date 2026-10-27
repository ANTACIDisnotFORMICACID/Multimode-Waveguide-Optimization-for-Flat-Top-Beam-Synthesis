"""Compare an HFSS port mode to the ideal-horn TE10 reference, without relabeling it.

The returned metrics describe a candidate association only. A port-eigenfield
correlation is still required to identify a TE/TM mode conclusively.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


COMPONENTS = ("EThetaReal", "EThetaImag", "EPhiReal", "EPhiImag")


def read_pattern(path: Path, port_mode: int | None = None) -> dict[str, list[dict]]:
    cuts: dict[str, list[dict]] = {"E": [], "H": []}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            if port_mode is not None and int(row["PortMode"]) != port_mode:
                continue
            plane = row["Plane"]
            if plane not in cuts:
                raise ValueError(f"Unexpected plane: {plane}")
            theta = float(row["ThetaDeg"])
            components = [float(row[key]) for key in COMPONENTS]
            if not all(math.isfinite(value) for value in [theta, *components]):
                raise ValueError("Non-finite pattern sample")
            cuts[plane].append({"theta": theta, "components": components,
                                "power": sum(value * value for value in components)})
    for plane, values in cuts.items():
        if not values:
            raise ValueError(f"Missing {plane}-plane pattern")
        if any(a["theta"] >= b["theta"] for a, b in zip(values, values[1:])):
            raise ValueError(f"Unsorted or repeated {plane}-plane angles")
    return cuts


def hpbw(theta: list[float], db: list[float], peak: int) -> float:
    left = next((index for index in range(peak - 1, -1, -1)
                 if db[index] <= -3.0), None)
    right = next((index for index in range(peak + 1, len(db))
                  if db[index] <= -3.0), None)
    if left is None or right is None:
        return math.nan

    def crossing(a: int, b: int) -> float:
        return theta[a] + (-3.0 - db[a]) * (theta[b] - theta[a]) / (db[b] - db[a])

    return crossing(right - 1, right) - crossing(left, left + 1)


def compare(reference: dict[str, list[dict]], hfss: dict[str, list[dict]]):
    metrics = []
    traces = []
    for plane in ("E", "H"):
        a, b = reference[plane], hfss[plane]
        if len(a) != len(b) or any(abs(x["theta"] - y["theta"]) > 1e-9
                                   for x, y in zip(a, b)):
            raise ValueError(f"Reference/HFSS {plane}-plane grids differ")
        theta = [sample["theta"] for sample in a]
        ref_max = max(sample["power"] for sample in a)
        hfss_max = max(sample["power"] for sample in b)
        if ref_max <= 0 or hfss_max <= 0:
            raise ValueError("Zero-power pattern")
        ref_db = [10 * math.log10(max(sample["power"] / ref_max, 1e-12)) for sample in a]
        hfss_db = [10 * math.log10(max(sample["power"] / hfss_max, 1e-12)) for sample in b]
        ref_peak = max(range(len(theta)), key=lambda index: ref_db[index])
        hfss_peak = max(range(len(theta)), key=lambda index: hfss_db[index])
        # The union retains disagreements where either curve still exceeds
        # -20 dB; an intersection could hide an unexpectedly deep null.
        visible = [index for index in range(len(theta))
                   if max(ref_db[index], hfss_db[index]) > -20]
        rmse = math.sqrt(sum((ref_db[index] - hfss_db[index]) ** 2
                             for index in visible) / len(visible))
        ref_width = hpbw(theta, ref_db, ref_peak)
        hfss_width = hpbw(theta, hfss_db, hfss_peak)
        metrics.append({"Plane": plane, "ReferencePeakDeg": theta[ref_peak],
                        "HfssPeakDeg": theta[hfss_peak],
                        "PeakDifferenceDeg": abs(theta[ref_peak] - theta[hfss_peak]),
                        "ReferenceHpbwDeg": ref_width, "HfssHpbwDeg": hfss_width,
                        "HpbwRelativeDifference": abs(hfss_width - ref_width) / ref_width,
                        "PatternRmseDbAboveMinus20": rmse,
                        "ComparisonSamples": len(visible)})
        for angle, r_db, h_db in zip(theta, ref_db, hfss_db):
            traces.append({"Plane": plane, "ThetaDeg": angle,
                           "ReferenceDb": r_db, "HfssDb": h_db,
                           "DifferenceDb": h_db - r_db})
    return metrics, traces


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("hfss_patterns", type=Path)
    parser.add_argument("--port-mode", type=int, default=1)
    parser.add_argument("--reference-model", default="ideal_adiabatic_horn_aperture")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        parser.error("Output directory already exists")
    metrics, traces = compare(read_pattern(args.reference),
                              read_pattern(args.hfss_patterns, args.port_mode))
    output.mkdir(parents=True)
    with (output / "pattern_overlay.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(traces[0]))
        writer.writeheader()
        writer.writerows(traces)
    summary = {"port_mode": args.port_mode,
               "analytic_mode_status": "TE10_CANDIDATE_NOT_PORT_FIELD_IDENTIFIED",
               "reference_model": args.reference_model,
               "power_normalization": "each plane normalized to its own peak",
               "comparison_region": "union of normalized values above -20 dB",
               "metrics": metrics}
    (output / "comparison_metrics.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
