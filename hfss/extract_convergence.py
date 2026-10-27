"""Extract HFSS adaptive-pass evidence from an AEDT EMConvData file.

The file can be updated while HFSS is solving. A parsed pass history is not a
completed-solve certificate; only call this on a saved, completed project.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def _match(text: str, pattern: str, label: str) -> str:
    result = re.search(pattern, text)
    if not result:
        raise ValueError(f"Missing {label} in EMConvData")
    return result.group(1)


def parse_convergence(path: Path) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    target = float(_match(raw, r"ConvTarget='([^']+)'", "target"))
    required = int(_match(raw, r"ConvTargetConsecPasses='([^']+)'", "consecutive-pass target"))
    current = int(_match(raw, r"ConvCurrentConsecPasses='([^']+)'", "consecutive-pass count"))
    reported = _match(raw, r"IsConverged=(true|false)", "convergence flag") == "true"
    blocks = re.findall(r"\$begin 'QuantityValues'(.*?)\$end 'QuantityValues'", raw, re.S)
    passes: dict[int, dict[str, float | int | None]] = {}
    for block in blocks:
        # The same pass is stored once with blank intrinsics and once with the
        # frequency. Prefer the explicit 30 GHz entry, never double count it.
        explicit_frequency = "30000000000" in block
        if "Intrinsics=''" not in block and not explicit_frequency:
            continue
        number = int(_match(block, r"PassNo=(\d+)", "pass number"))
        elements = float(_match(block, r"SolvedElements\(([^,]+),", "solved elements"))
        delta_match = re.search(r"MaxMagDeltaS\(([^,]+),", block)
        delta = float(delta_match.group(1)) if delta_match else None
        if number not in passes or explicit_frequency:
            passes[number] = {"PassNo": number, "SolvedElements": int(elements),
                              "MaxMagDeltaS": delta}
    ordered = [passes[key] for key in sorted(passes)]
    if not ordered or [row["PassNo"] for row in ordered] != list(range(1, len(ordered) + 1)):
        raise ValueError("Adaptive pass sequence is empty or has gaps")
    return {"source": str(path.resolve()), "delta_s_target": target,
            "required_consecutive_passes": required,
            "reported_consecutive_passes": current,
            "reported_is_converged": reported,
            "target_reached_for_required_passes": reported and current >= required,
            "passes": ordered}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("emconvdata", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = parse_convergence(args.emconvdata)
    if args.output_dir:
        output = args.output_dir.resolve()
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite {output}")
        output.mkdir(parents=True)
        with (output / "mesh_convergence.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["PassNo", "SolvedElements", "MaxMagDeltaS"])
            writer.writeheader()
            writer.writerows(result["passes"])
        (output / "mesh_convergence_receipt.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
