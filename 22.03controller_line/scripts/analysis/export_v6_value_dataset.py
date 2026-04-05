#!/usr/bin/env python3
"""
Export V6 value-model training rows from simulation_results.json payloads.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_CODE_DIR = _REPO_ROOT / "code"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

from simulation.v6_value_model import (
    DEFAULT_V6B2_TRAIN_ENDPOINTS,
    collect_value_dataset_rows,
    write_rows_to_csv,
)


DEFAULT_RESULTS_DIR = Path("data/results/EXP_EXP01")
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "_analysis_v6_value"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export V6 value-model dataset")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--endpoints", nargs="*", default=None)
    parser.add_argument("--filter-policy", default="none")
    parser.add_argument("--lambda-deadline", type=float, default=40.0)
    parser.add_argument("--lambda-gap", type=float, default=5.0)
    args = parser.parse_args()

    if args.endpoints:
        endpoints = set(args.endpoints)
    elif str(args.filter_policy).lower() == "v6b2_only":
        endpoints = set(DEFAULT_V6B2_TRAIN_ENDPOINTS)
    else:
        endpoints = None
    rows = collect_value_dataset_rows(
        results_dir=args.results_dir,
        endpoints=endpoints,
        filter_policy=str(args.filter_policy),
        lambda_deadline=float(args.lambda_deadline),
        lambda_gap=float(args.lambda_gap),
    )
    if not rows:
        print(f"No rows found under {args.results_dir}")
        return 1

    output_dir = Path(args.output_dir)
    csv_path = write_rows_to_csv(output_dir / "v6_value_dataset.csv", rows)
    manifest = {
        "results_dir": str(args.results_dir),
        "row_count": len(rows),
        "endpoints": sorted(set(str(row["endpoint"]) for row in rows)),
        "targets": [
            "target_failures_to_go",
            "target_cost_to_go",
            "target_penalized_to_go",
            "target_deadline_pressure_to_go",
            "target_service_gap_to_go",
            "target_value_to_go",
        ],
        "filter_policy": str(args.filter_policy),
        "lambda_deadline": float(args.lambda_deadline),
        "lambda_gap": float(args.lambda_gap),
        "csv_path": str(csv_path),
    }
    manifest_path = output_dir / "v6_value_dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(csv_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
