#!/usr/bin/env python3
"""
Aggregate Scenario1 results across endpoints.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean, stdev

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.results_layout import endpoint_name_from_result_file


DEFAULT_RESULTS_DIR = Path("data/results/EXP_EXP01")
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "_analysis_scenario1"
METRICS = [
    "service_rate",
    "failed_orders",
    "cost_raw",
    "penalized_cost",
    "cost_per_order",
    "plan_churn",
    "load_mse",
]


def collect_rows(results_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(results_dir.glob("**/summary_final.json")):
        if "_analysis" in path.parts:
            continue
        seed_part = next((part for part in path.parts if part.startswith("Seed_")), None)
        if seed_part is None:
            continue
        endpoint = endpoint_name_from_result_file(path, results_dir=results_dir)
        endpoint = "scenario1_baseline" if endpoint == "baseline" else endpoint
        seed = int(seed_part.split("_", 1)[1])
        data = json.loads(path.read_text())
        row = {"endpoint": endpoint, "seed": seed, "strategy": data.get("strategy", ""), "summary_path": str(path)}
        for metric in METRICS:
            row[metric] = float(data.get(metric))
        rows.append(row)
    return rows


def aggregate_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["endpoint"]), []).append(row)
    out: list[dict[str, object]] = []
    for endpoint, group in sorted(grouped.items()):
        for metric in METRICS:
            values = [float(row[metric]) for row in group]
            out.append(
                {
                    "endpoint": endpoint,
                    "metric": metric,
                    "n": len(values),
                    "mean": mean(values),
                    "std": stdev(values) if len(values) > 1 else 0.0,
                    "min": min(values),
                    "max": max(values),
                }
            )
    return out


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate Scenario1 suite")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    rows = collect_rows(Path(args.results_dir))
    if not rows:
        print(f"No Scenario1 summaries found under {args.results_dir}")
        return 1
    agg = aggregate_rows(rows)
    out_dir = Path(args.output_dir)
    write_csv(out_dir / "scenario1_per_seed.csv", rows, ["endpoint", "seed", "strategy", *METRICS, "summary_path"])
    write_csv(out_dir / "scenario1_aggregate.csv", agg, ["endpoint", "metric", "n", "mean", "std", "min", "max"])
    print(out_dir / "scenario1_per_seed.csv")
    print(out_dir / "scenario1_aggregate.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
