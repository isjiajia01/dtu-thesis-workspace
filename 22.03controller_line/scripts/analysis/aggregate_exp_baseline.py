#!/usr/bin/env python3
"""
Aggregate EXP-BASELINE results across seeds.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, stdev


DEFAULT_RESULTS_DIR = Path("data/results/EXP_EXP-BASELINE")
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "_analysis"
METRICS = [
    "service_rate",
    "failed_orders",
    "cost_raw",
    "penalized_cost",
    "cost_per_order",
    "plan_churn",
    "load_mse",
]


def _safe_float(value) -> float:
    if value is None:
        return float("nan")
    return float(value)


def collect_rows(results_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(results_dir.glob("**/summary_final.json")):
        if "_analysis" in path.parts:
            continue
        seed_part = next((part for part in path.parts if part.startswith("Seed_")), None)
        if seed_part is None:
            continue
        seed = int(seed_part.split("_", 1)[1])
        data = json.loads(path.read_text())
        row = {
            "seed": seed,
            "summary_path": str(path),
            "strategy": data.get("strategy", ""),
        }
        for metric in METRICS:
            row[metric] = _safe_float(data.get(metric))
        rows.append(row)
    return rows


def aggregate_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    aggregates: list[dict[str, object]] = []
    for metric in METRICS:
        values = [float(row[metric]) for row in rows]
        metric_mean = mean(values)
        metric_std = stdev(values) if len(values) > 1 else 0.0
        aggregates.append(
            {
                "metric": metric,
                "n": len(values),
                "mean": metric_mean,
                "std": metric_std,
                "min": min(values),
                "max": max(values),
            }
        )
    return aggregates


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, object]], aggregates: list[dict[str, object]]) -> None:
    lines = [
        "# EXP-BASELINE Aggregate Report",
        "",
        f"- Seeds aggregated: `{len(rows)}`",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Mean | Std | Min | Max |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in aggregates:
        lines.append(
            f"| {row['metric']} | {float(row['mean']):.6f} | {float(row['std']):.6f} | {float(row['min']):.6f} | {float(row['max']):.6f} |"
        )
    lines.extend(
        [
            "",
            "## Per-Seed Files",
            "",
            "| Seed | Strategy | Summary Path |",
            "| --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(f"| {row['seed']} | {row['strategy']} | `{row['summary_path']}` |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate EXP-BASELINE results")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR), help="Root results directory")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Aggregation output directory")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    rows = collect_rows(results_dir)
    if not rows:
        print(f"No summary_final.json files found under {results_dir}")
        return 1

    aggregates = aggregate_rows(rows)
    per_seed_csv = output_dir / "exp_baseline_per_seed.csv"
    aggregate_csv = output_dir / "exp_baseline_aggregate.csv"
    report_md = output_dir / "exp_baseline_report.md"

    write_csv(per_seed_csv, rows, ["seed", "strategy", *METRICS, "summary_path"])
    write_csv(aggregate_csv, aggregates, ["metric", "n", "mean", "std", "min", "max"])
    write_markdown(report_md, rows, aggregates)

    print(f"Wrote {per_seed_csv}")
    print(f"Wrote {aggregate_csv}")
    print(f"Wrote {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
