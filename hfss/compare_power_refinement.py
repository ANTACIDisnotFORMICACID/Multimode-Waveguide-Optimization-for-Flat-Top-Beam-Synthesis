"""Compare native HFSS antenna-power reports before and after mesh refinement."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def native_rows(path: Path) -> dict[str, dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    selected = {row["case"]: row for row in rows
                if row["include_port_post_processing"].lower() == "false"}
    if len(selected) != len([row for row in rows
                             if row["include_port_post_processing"].lower() == "false"]):
        raise ValueError(f"Duplicate intrinsic case in {path}")
    if not selected:
        raise ValueError(f"No intrinsic excitation rows in {path}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_csv", type=Path)
    parser.add_argument("refined_csv", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    baseline, refined = native_rows(args.baseline_csv), native_rows(args.refined_csv)
    if baseline.keys() != refined.keys():
        raise ValueError("Baseline and refined intrinsic source cases differ")
    rows = []
    for case in baseline:
        before, after = baseline[case], refined[case]
        old_in = float(before["IncidentPower"])
        new_in = float(after["IncidentPower"])
        if abs(old_in - new_in) > 1e-5 * max(old_in, new_in, 1):
            raise ValueError(f"Source incident power changed for {case}")
        old_a, new_a = float(before["AcceptedPower"]), float(after["AcceptedPower"])
        old_r, new_r = float(before["RadiatedPower"]), float(after["RadiatedPower"])
        if min(old_a, new_a, old_r, new_r) <= 0:
            raise ValueError(f"Nonpositive antenna power for {case}")
        rows.append({"case": case,
                     "incident_power_w": new_in,
                     "baseline_accepted_w": old_a,
                     "refined_accepted_w": new_a,
                     "baseline_radiated_w": old_r,
                     "refined_radiated_w": new_r,
                     "baseline_power_imbalance_pct": 100 * (old_r / old_a - 1),
                     "refined_power_imbalance_pct": 100 * (new_r / new_a - 1),
                     "radiated_change_pct": 100 * (new_r / old_r - 1),
                     "accepted_change_pct": 100 * (new_a / old_a - 1)})
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "power_refinement_comparison.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "receipt.json").write_text(json.dumps({
        "status": "POWER_REFINEMENT_COMPARED",
        "baseline_csv": str(args.baseline_csv),
        "refined_csv": str(args.refined_csv),
        "case_count": len(rows),
        "note": "Numerical imbalance is reported, not silently converted into efficiency.",
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
