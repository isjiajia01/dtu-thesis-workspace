#!/usr/bin/env python3
"""
Aggregate experiment-suite results by endpoint while avoiding duplicate summary files.
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

from src.results_layout import iter_endpoint_dirs as iter_nested_endpoint_dirs


DEFAULT_RESULTS_DIR = Path("data/results/EXP_EXP01")
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "_analysis_suite"
METRICS = [
    "service_rate",
    "failed_orders",
    "cost_raw",
    "penalized_cost",
    "cost_per_order",
    "plan_churn",
    "load_mse",
]
EXTRA_FIELDS = [
    "eligible_count",
    "days_completed",
    "days_total",
    "is_partial",
    "partial_status",
]


def _safe_float(value) -> float:
    if value is None:
        return float("nan")
    return float(value)


def _safe_int(value) -> int | None:
    if value is None:
        return None
    return int(value)


def choose_summary_path(seed_dir: Path) -> Path | None:
    direct = seed_dir / "summary_final.json"
    if direct.exists():
        return direct

    proactive = seed_dir / "DEFAULT" / "Proactive" / "summary_final.json"
    if proactive.exists():
        return proactive

    candidates = sorted(seed_dir.glob("**/summary_final.json"))
    return candidates[0] if candidates else None


def iter_endpoint_dirs(results_dir: Path) -> list[Path]:
    return list(iter_nested_endpoint_dirs(results_dir))


def collect_rows(results_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for endpoint_dir in iter_endpoint_dirs(results_dir):
        endpoint = endpoint_dir.name
        for seed_dir in sorted(endpoint_dir.glob("Seed_*")):
            summary_path = choose_summary_path(seed_dir)
            if summary_path is None:
                continue
            data = json.loads(summary_path.read_text())
            row: dict[str, object] = {
                "endpoint": endpoint,
                "seed": int(seed_dir.name.split("_", 1)[1]),
                "strategy": data.get("strategy", ""),
                "summary_path": str(summary_path),
            }
            for metric in METRICS:
                row[metric] = _safe_float(data.get(metric))
            row["eligible_count"] = _safe_int(data.get("eligible_count"))
            row["days_completed"] = _safe_int(data.get("days_completed"))
            row["days_total"] = _safe_int(data.get("days_total"))
            row["is_partial"] = bool(data.get("is_partial", False))
            row["partial_status"] = str(data.get("partial_status", ""))
            rows.append(row)
    return rows


def aggregate_metric(values: list[float]) -> tuple[float, float, float, float]:
    metric_mean = mean(values)
    metric_std = stdev(values) if len(values) > 1 else 0.0
    return metric_mean, metric_std, min(values), max(values)


def build_endpoint_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["endpoint"]), []).append(row)

    out: list[dict[str, object]] = []
    for endpoint, group in sorted(grouped.items()):
        seeds = sorted(int(row["seed"]) for row in group)
        strategies = sorted({str(row["strategy"]) for row in group if row["strategy"]})
        partial_count = sum(1 for row in group if bool(row["is_partial"]))

        eligible_values = [int(row["eligible_count"]) for row in group if row["eligible_count"] is not None]
        days_completed = [int(row["days_completed"]) for row in group if row["days_completed"] is not None]
        days_total = [int(row["days_total"]) for row in group if row["days_total"] is not None]

        summary: dict[str, object] = {
            "endpoint": endpoint,
            "n_seeds": len(group),
            "seed_list": ",".join(str(seed) for seed in seeds),
            "strategies": ",".join(strategies),
            "partial_count": partial_count,
            "all_completed": partial_count == 0,
            "eligible_count_mean": mean(eligible_values) if eligible_values else float("nan"),
            "days_completed_min": min(days_completed) if days_completed else None,
            "days_completed_max": max(days_completed) if days_completed else None,
            "days_total_min": min(days_total) if days_total else None,
            "days_total_max": max(days_total) if days_total else None,
        }

        for metric in METRICS:
            values = [float(row[metric]) for row in group]
            metric_mean, metric_std, metric_min, metric_max = aggregate_metric(values)
            summary[f"{metric}_mean"] = metric_mean
            summary[f"{metric}_std"] = metric_std
            summary[f"{metric}_min"] = metric_min
            summary[f"{metric}_max"] = metric_max

        out.append(summary)

    return sorted(
        out,
        key=lambda row: (
            -float(row["service_rate_mean"]),
            float(row["failed_orders_mean"]),
            float(row["penalized_cost_mean"]),
            str(row["endpoint"]),
        ),
    )


def build_metric_aggregate(endpoint_summary: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for summary in endpoint_summary:
        endpoint = str(summary["endpoint"])
        n = int(summary["n_seeds"])
        for metric in METRICS:
            rows.append(
                {
                    "endpoint": endpoint,
                    "metric": metric,
                    "n": n,
                    "mean": summary[f"{metric}_mean"],
                    "std": summary[f"{metric}_std"],
                    "min": summary[f"{metric}_min"],
                    "max": summary[f"{metric}_max"],
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, suite_name: str, endpoint_summary: list[dict[str, object]]) -> None:
    lines = [
        f"# {suite_name} Aggregate Report",
        "",
        f"- Endpoints aggregated: `{len(endpoint_summary)}`",
        f"- Fully completed endpoints: `{sum(1 for row in endpoint_summary if bool(row['all_completed']))}`",
        f"- Incomplete endpoints: `{sum(1 for row in endpoint_summary if not bool(row['all_completed']))}`",
        "",
        "## Endpoint Ranking",
        "",
        "Sorted by `service_rate_mean desc`, then `failed_orders_mean asc`, then `penalized_cost_mean asc`.",
        "",
        "| Endpoint | Seeds | Partial | Service Rate | Failed Orders | Penalized Cost | Raw Cost | Cost/Order | Plan Churn | Load MSE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in endpoint_summary:
        lines.append(
            "| {endpoint} | {n_seeds} | {partial_count} | {service_rate_mean:.6f} | {failed_orders_mean:.3f} | {penalized_cost_mean:.3f} | {cost_raw_mean:.3f} | {cost_per_order_mean:.6f} | {plan_churn_mean:.6f} | {load_mse_mean:.3f} |".format(
                **row
            )
        )

    incomplete = [row for row in endpoint_summary if not bool(row["all_completed"])]
    if incomplete:
        lines.extend(
            [
                "",
                "## Incomplete Endpoints",
                "",
                "| Endpoint | Seeds | Partial | Seed List | Days Completed | Days Total |",
                "| --- | ---: | ---: | --- | --- | --- |",
            ]
        )
        for row in incomplete:
            lines.append(
                f"| {row['endpoint']} | {row['n_seeds']} | {row['partial_count']} | `{row['seed_list']}` | {row['days_completed_min']}-{row['days_completed_max']} | {row['days_total_min']}-{row['days_total_max']} |"
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate experiment suite results by endpoint")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--suite-name", default="")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    suite_name = args.suite_name or results_dir.name

    rows = collect_rows(results_dir)
    if not rows:
        print(f"No canonical summary_final.json files found under {results_dir}")
        return 1

    endpoint_summary = build_endpoint_summary(rows)
    metric_aggregate = build_metric_aggregate(endpoint_summary)

    per_seed_csv = output_dir / "suite_per_seed.csv"
    endpoint_csv = output_dir / "suite_endpoint_summary.csv"
    aggregate_csv = output_dir / "suite_metric_aggregate.csv"
    report_md = output_dir / "suite_report.md"

    write_csv(per_seed_csv, rows, ["endpoint", "seed", "strategy", *METRICS, *EXTRA_FIELDS, "summary_path"])
    write_csv(
        endpoint_csv,
        endpoint_summary,
        [
            "endpoint",
            "n_seeds",
            "seed_list",
            "strategies",
            "partial_count",
            "all_completed",
            "eligible_count_mean",
            "days_completed_min",
            "days_completed_max",
            "days_total_min",
            "days_total_max",
            *[f"{metric}_{suffix}" for metric in METRICS for suffix in ("mean", "std", "min", "max")],
        ],
    )
    write_csv(aggregate_csv, metric_aggregate, ["endpoint", "metric", "n", "mean", "std", "min", "max"])
    write_markdown(report_md, suite_name, endpoint_summary)

    print(per_seed_csv)
    print(endpoint_csv)
    print(aggregate_csv)
    print(report_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
