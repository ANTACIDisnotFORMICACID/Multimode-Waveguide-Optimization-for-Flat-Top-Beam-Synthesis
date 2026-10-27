"""Compare native HFSS port propagation constants with analytic cutoff data.

Degenerate modes share beta, so dispersion identifies mode groups rather than
unique TE/TM port-field identities. Port Zo depends on HFSS's port impedance
definition and calibration and is not substituted for analytic TE/TM impedance.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def validate(metadata_dir: Path, catalog_file: Path, output_dir: Path) -> dict:
    receipt = json.loads((metadata_dir / "export_receipt.json").read_text(encoding="utf-8"))
    if receipt.get("status") != "EXPORTED_UNVERIFIED" or receipt.get("analysis_called"):
        raise ValueError("Native modal export was not completed safely")
    if receipt.get("project_saved"):
        raise ValueError("Exporter unexpectedly saved the project")
    count = int(receipt["port_modes"])
    with (metadata_dir / "port_modal_data_30ghz.csv").open(
            newline="", encoding="utf-8") as stream:
        raw = list(csv.DictReader(stream))
    if len(raw) != 2 * count:
        raise ValueError("Expected one Gamma and one Zo per port mode")
    modal = {}
    for row in raw:
        index = int(row["PortMode"])
        key = row["Quantity"]
        if not 1 <= index <= count or key not in ("Gamma", "Port Zo"):
            raise ValueError("Invalid port index or quantity")
        value = complex(float(row["Real"]), float(row["Imag"]))
        if not math.isfinite(value.real) or not math.isfinite(value.imag):
            raise ValueError("Nonfinite native modal property")
        if (index, key) in modal:
            raise ValueError("Duplicate native modal property")
        modal[index, key] = value
    if len(modal) != 2 * count:
        raise ValueError("Incomplete native modal property grid")
    with catalog_file.open(newline="", encoding="utf-8") as stream:
        catalog = [row for row in csv.DictReader(stream)
                   if row["Status"] == "propagating"]
    if len(catalog) != count:
        raise ValueError("Analytic and HFSS propagating mode counts differ")
    analytic = sorted(catalog, key=lambda row: float(row["betaRadPerM"]), reverse=True)
    hfss = sorted(range(1, count + 1), key=lambda i: modal[i, "Gamma"].imag,
                  reverse=True)
    comparisons = []
    for mode_index, row in zip(hfss, analytic):
        beta = float(row["betaRadPerM"])
        observed = modal[mode_index, "Gamma"].imag
        candidates = [candidate["Name"] for candidate in catalog
                      if abs(float(candidate["betaRadPerM"]) - beta) < 1e-7]
        comparisons.append({
            "PortMode": mode_index,
            "CandidateModesByBeta": "|".join(candidates),
            "AnalyticBetaRadPerM": beta,
            "HfssGammaImagPerM": observed,
            "HfssGammaRealPerM": modal[mode_index, "Gamma"].real,
            "RelativeBetaErrorPct": 100 * abs(observed - beta) / beta,
            "ReportedZoOhm": modal[mode_index, "Port Zo"].real,
            "ReportedZoImagOhm": modal[mode_index, "Port Zo"].imag,
        })
    output_dir.mkdir(parents=True, exist_ok=False)
    with (output_dir / "modal_dispersion_comparison.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    port_only = receipt.get("setup_sweep") == "PortOnly30GHz : PortOnly"
    summary = {
        "status": "DISPERSION_GROUPS_COMPARED",
        "port_modes": count,
        "source": str(metadata_dir.resolve()),
        "max_relative_beta_error_pct": max(
            row["RelativeBetaErrorPct"] for row in comparisons),
        "near_cutoff_port_modes": [row["PortMode"] for row in comparisons
                                   if row["AnalyticBetaRadPerM"] < 100],
        "port_zo_interpretation": (
            "PORT ONLY MODAL ZO; PORT CONFIGURED FOR ZPI, NOT ANALYTIC TE/TM WAVE Z"
            if port_only else
            "FULL-WAVE REPORT ZO; CHECK RENORMALIZATION BEFORE COMPARING WITH TE/TM Z"),
        "mode_identity": "DEGENERATE GROUP ONLY; PORT EIGENFIELDS STILL NEEDED",
    }
    (output_dir / "validation_receipt.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata_dir", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.metadata_dir, args.catalog, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
