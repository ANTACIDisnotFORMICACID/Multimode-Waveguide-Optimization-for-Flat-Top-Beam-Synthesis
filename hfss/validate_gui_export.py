"""Check an AEDT GUI export before allowing it into the validation workflow.

This is intentionally an *import gate*, not a mode identifier or an HFSS/MATLAB
agreement claim. It keeps the native port-mode indices and complex field data.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


PORT_MODES = 10
PHIS = (0, 90, 180, 270)
FIELD_NAMES = ("EThetaReal", "EThetaImag", "EPhiReal", "EPhiImag")


def _finite(value: str, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} is not finite")
    return number


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"Missing export: {path.name}")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"Empty export: {path.name}")
    return rows


def validate_s_matrix(path: Path, port_modes: int = PORT_MODES) -> dict[str, object]:
    rows = _read_csv(path)
    entries: set[tuple[int, int]] = set()
    for row in rows:
        receive, source = int(row["ReceivePortMode"]), int(row["SourcePortMode"])
        key = (receive, source)
        if not 1 <= receive <= port_modes or not 1 <= source <= port_modes or key in entries:
            raise ValueError(f"Duplicate or invalid S-matrix index: {key}")
        entries.add(key)
        unit = row["FreqUnit"].strip().lower()
        frequency = _finite(row["FreqValue"], "frequency")
        frequency_hz = frequency * {"ghz": 1e9, "hz": 1.0}.get(unit, math.nan)
        if not math.isclose(frequency_hz, 30e9, rel_tol=1e-6):
            raise ValueError("S-matrix frequency is not 30 GHz")
        _finite(row["SReal"], "S real")
        _finite(row["SImag"], "S imaginary")
    if len(entries) != port_modes**2:
        raise ValueError(f"Expected {port_modes**2} complex S entries, got {len(entries)}")
    return {"s_matrix_entries": len(entries), "frequency_hz": 30e9}


def validate_complex_cuts(path: Path, port_modes: int = PORT_MODES) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows = _read_csv(path)
    grouped: dict[tuple[int, int], list[tuple[float, tuple[float, ...]]]] = defaultdict(list)
    for row in rows:
        mode, phi = int(row["PortMode"]), int(row["PhiDeg"])
        if not 1 <= mode <= port_modes or phi not in PHIS:
            raise ValueError(f"Invalid port mode or phi: {mode}, {phi}")
        theta = _finite(row["ThetaDeg"], "theta")
        fields = tuple(_finite(row[name], name) for name in FIELD_NAMES)
        grouped[(mode, phi)].append((theta, fields))
    if len(grouped) != port_modes * len(PHIS):
        raise ValueError(f"Expected {port_modes*len(PHIS)} mode/phi cuts, got {len(grouped)}")
    reference_grid: tuple[float, ...] | None = None
    for key, values in grouped.items():
        grid = tuple(item[0] for item in values)
        if len(grid) < 3 or abs(grid[0]) > 1e-6 or abs(grid[-1] - 90) > 1e-6:
            raise ValueError(f"Incomplete 0..90 degree theta grid for {key}")
        if any(not 0 < second - first <= 0.50001 for first, second in zip(grid, grid[1:])):
            raise ValueError(f"Unsorted, duplicated or coarse theta grid for {key}")
        if reference_grid is None:
            reference_grid = grid
        elif len(grid) != len(reference_grid) or any(
            abs(a - b) > 1e-6 for a, b in zip(grid, reference_grid)
        ):
            raise ValueError(f"Angular grid mismatch for {key}")

    # The negative signed cut uses phi+180 and a *reversed transverse basis*.
    # Both E_theta and E_phi acquire a minus sign. Keeping complex fields is
    # necessary for subsequent coherent multimode synthesis.
    signed: list[dict[str, object]] = []
    for mode in range(1, port_modes + 1):
        for plane, positive_phi, opposite_phi in (("E", 90, 270), ("H", 0, 180)):
            for theta, fields in reversed(grouped[(mode, opposite_phi)]):
                if theta > 0:
                    signed.append(_signed_row(mode, plane, -theta, tuple(-v for v in fields)))
            for theta, fields in grouped[(mode, positive_phi)]:
                signed.append(_signed_row(mode, plane, theta, fields))
    return {
        "port_mode_count": port_modes,
        "raw_mode_phi_cuts": len(grouped),
        "samples_per_cut": len(reference_grid or ()),
        "raw_complex_samples": len(rows),
        "signed_complex_samples": len(signed),
        "analytic_mode_identified": False,
    }, signed


def _signed_row(mode: int, plane: str, theta: float,
                fields: tuple[float, ...]) -> dict[str, object]:
    return {"PortMode": mode, "AnalyticMode": "UNIDENTIFIED", "Plane": plane,
            "ThetaDeg": theta, **dict(zip(FIELD_NAMES, fields))}


def validate_export(folder: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    receipt_path = folder / "export_receipt.json"
    if not receipt_path.is_file():
        raise ValueError("GUI export receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    native_data_checked = receipt.get("solved_data_checked") or (
        receipt.get("setup_is_solved") is True and
        receipt.get("theta_samples_phi0", 0) > 0 and
        len(receipt.get("s11_real", [])) == 1 and
        len(receipt.get("s11_imag", [])) == 1
    )
    if receipt.get("status") != "EXPORTED_UNVERIFIED" or not native_data_checked:
        raise ValueError("AEDT export did not finish with readable solved data")
    if receipt.get("analysis_called_by_script") or receipt.get("project_saved_by_script"):
        raise ValueError("GUI exporter unexpectedly changed the solve or saved project")
    port_modes = int(receipt.get("port_modes", PORT_MODES))
    if port_modes not in (10, 12):
        raise ValueError("Unsupported port-mode count")
    s_summary = validate_s_matrix(folder / "s_matrix_30ghz.csv", port_modes)
    cut_summary, signed = validate_complex_cuts(folder / "hfss_raw_complex_cuts.csv", port_modes)
    if receipt.get("complex_cut_samples") != cut_summary["raw_complex_samples"]:
        raise ValueError("Receipt and complex-cut row counts disagree")
    return {"status": "RAW_EXPORT_VALIDATED", "source_folder": str(folder.resolve()),
            "project": receipt.get("project"), **s_summary, **cut_summary}, signed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir", type=Path)
    parser.add_argument("--output-dir", type=Path,
                        help="Write checked cuts and audit JSON to a new directory")
    args = parser.parse_args()
    summary, signed = validate_export(args.export_dir)
    if args.output_dir:
        output = args.output_dir.resolve()
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite {output}")
        output.mkdir(parents=True)
        with (output / "hfss_port_mode_patterns.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(signed[0]))
            writer.writeheader()
            writer.writerows(signed)
        (output / "validation_receipt.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
