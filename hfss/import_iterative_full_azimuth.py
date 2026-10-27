"""Validate GUI-exported 15-pass FFDs against independent complex cuts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from compare_iterative_cuts import PHIS, THETA, read_new_cuts
from export_dense_embedded import read_ffd, read_mapping


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gui_output", type=Path)
    parser.add_argument("independent_cuts", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        parser.error("Output directory already exists")
    gui = args.gui_output.resolve()
    receipt = json.loads((gui / "receipt.json").read_text(encoding="utf-8"))
    if (receipt.get("status") != "FULL_AZIMUTH_FFD_EXPORTED_UNVERIFIED" or
            receipt.get("analysis_called") or receipt.get("project_saved_by_script") or
            receipt.get("include_port_post_processing") is not False or
            receipt.get("setup") != "PowerCheck30GHz : LastAdaptive"):
        raise ValueError("GUI export receipt does not identify the expected 15-pass basis")
    mapping = read_mapping(gui / "eep.txt")
    phi_expected = np.arange(0.0, 360.0, 5.0)
    fields = np.empty((12, THETA.size, phi_expected.size, 2), dtype=np.complex128)
    hashes = {}
    for mode, path in sorted(mapping.items()):
        theta, phi, field = read_ffd(path)
        if not np.array_equal(theta, THETA) or not np.array_equal(phi, phi_expected):
            raise ValueError(f"Unexpected FFD grid for port {mode}")
        fields[mode - 1] = field
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = read_new_cuts(args.independent_cuts)
    four_rays = np.transpose(fields[:, :, [angle // 5 for angle in PHIS], :],
                             (0, 2, 1, 3)) * 1000.0
    complex_l2 = float(np.linalg.norm(four_rays - report) / np.linalg.norm(report))
    if complex_l2 > 1e-7:
        raise ValueError(f"FFD and independent GUI cuts disagree: {complex_l2:.3g}")
    output.mkdir(parents=True)
    np.savez_compressed(output / "complex_modal_basis.npz",
                        theta_deg=THETA, phi_deg=phi_expected,
                        port_modes=np.arange(1, 13),
                        e_theta=fields[..., 0], e_phi=fields[..., 1])
    (output / "receipt.json").write_text(json.dumps({
        "status": "FULL_AZIMUTH_FFD_CROSSCHECKED",
        "gui_output": str(gui),
        "independent_cuts": str(args.independent_cuts.resolve()),
        "mode_count": 12,
        "theta_samples": int(THETA.size),
        "phi_samples": int(phi_expected.size),
        "four_ray_complex_l2_error": complex_l2,
        "empirical_ffd_to_report_factor": 1000.0,
        "ffd_sha256": hashes,
        "analysis_called": False,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"15-pass FFD vs direct complex cuts relative L2: {complex_l2:.3g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
