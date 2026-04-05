#!/usr/bin/env python3
"""
Audit residual failures between V6 controller variants during the shock window.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.results_layout import find_endpoint_dir


DEFAULT_RESULTS_DIR = Path("data/results/EXP_EXP01")
DEFAULT_DATA_PATH = Path("data/processed/multiday_benchmark_herlev.json")
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "_analysis_scenario1"
DEFAULT_BASELINE_ENDPOINT = "scenario1_robust_v6b2_guarded_value_rerank_compute300"
DEFAULT_CANDIDATE_ENDPOINT = "scenario1_robust_v6e_phase_guarded_compute300"
DEFAULT_REFERENCE_ENDPOINTS = [
    "scenario1_robust_v6b2_guarded_value_rerank_compute300",
    "scenario1_robust_v6d_value_model_refit_compute300",
]
SHOCK_WINDOW = {"2025-12-06", "2025-12-07", "2025-12-08", "2025-12-09"}


def _route_burden(order: dict, depot_loc) -> float:
    loc = order.get("location") or [0.0, 0.0]
    return math.hypot(float(loc[0]) - float(depot_loc[0]), float(loc[1]) - float(depot_loc[1]))


def _load_run_id(results_dir: Path, endpoint: str, seed: int) -> str:
    summary_path = find_endpoint_dir(results_dir, endpoint) / f"Seed_{seed}" / "summary_final.json"
    payload = json.loads(summary_path.read_text())
    return str(payload["run_id"])


def _load_failed_orders(results_dir: Path, endpoint: str, seed: int) -> list[dict[str, object]]:
    run_id = _load_run_id(results_dir, endpoint, seed)
    path = results_dir.parent / run_id / "DEFAULT" / "Proactive" / "failed_orders.csv"
    rows: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["id"] = int(row["id"])
            rows.append(row)
    return rows


def _load_daily_stats(results_dir: Path, endpoint: str, seed: int) -> list[dict[str, object]]:
    path = find_endpoint_dir(results_dir, endpoint) / f"Seed_{seed}" / "simulation_results.json"
    payload = json.loads(path.read_text())
    return list(payload.get("daily_stats", []))


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_counter(counter: Counter) -> str:
    if not counter:
        return "{}"
    return "{ " + ", ".join(f"{k}: {v}" for k, v in sorted(counter.items())) + " }"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit residual failures between V6 variants")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--data-path", default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--candidate-endpoint", default=DEFAULT_CANDIDATE_ENDPOINT)
    parser.add_argument("--reference-endpoints", nargs="*", default=DEFAULT_REFERENCE_ENDPOINTS)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    raw = json.loads(Path(args.data_path).read_text())
    orders = {int(order["id"]): order for order in raw["orders"]}
    depot_loc = raw["depot"]["location"]

    delta_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    action_rows: list[dict[str, object]] = []

    for reference_endpoint in args.reference_endpoints:
        extra_counter = Counter()
        avoided_counter = Counter()
        reason_counter = Counter()
        window_counter = Counter()
        profile_counter = Counter()
        flags_counter = Counter()
        extra_ids = Counter()
        extra_route = []
        extra_demand = []
        extra_service = []
        extra_flex = []

        for seed in range(1, 11):
            candidate_failed = _load_failed_orders(results_dir, args.candidate_endpoint, seed)
            reference_failed = _load_failed_orders(results_dir, reference_endpoint, seed)
            candidate_by_id = {int(row["id"]): row for row in candidate_failed}
            reference_by_id = {int(row["id"]): row for row in reference_failed}
            candidate_ids = set(candidate_by_id)
            reference_ids = set(reference_by_id)

            for label, source_rows, ids in (
                ("extra_fail", candidate_by_id, candidate_ids - reference_ids),
                ("avoided_fail", reference_by_id, reference_ids - candidate_ids),
            ):
                for oid in sorted(ids):
                    row = dict(source_rows[oid])
                    order = orders[int(oid)]
                    demand_colli = float(order.get("demand", {}).get("colli", 0.0))
                    service_time = float(order.get("service_time", 0.0))
                    route_burden = _route_burden(order, depot_loc)
                    delivery_window_days = int(order.get("delivery_window_days", 0) or 0)
                    is_flexible = bool(order.get("is_flexible", False))
                    out = {
                        "seed": seed,
                        "compare_to": reference_endpoint,
                        "delta_kind": label,
                        "id": int(oid),
                        "fail_date": str(row["fail_date"]),
                        "deadline": str(row["deadline"]),
                        "release_date": str(row["release_date"]),
                        "reason": str(row["reason"]),
                        "delivery_window_days": delivery_window_days,
                        "is_flexible": int(is_flexible),
                        "demand_colli": demand_colli,
                        "service_time": service_time,
                        "route_burden": route_burden,
                    }
                    delta_rows.append(out)
                    if label == "extra_fail":
                        extra_counter[str(row["fail_date"])] += 1
                        reason_counter[str(row["reason"])] += 1
                        window_counter[str(delivery_window_days)] += 1
                        extra_ids[int(oid)] += 1
                        extra_route.append(route_burden)
                        extra_demand.append(demand_colli)
                        extra_service.append(service_time)
                        extra_flex.append(1 if is_flexible else 0)
                    else:
                        avoided_counter[str(row["fail_date"])] += 1

            candidate_daily = _load_daily_stats(results_dir, args.candidate_endpoint, seed)
            for row in candidate_daily:
                date = str(row.get("date"))
                if date not in SHOCK_WINDOW:
                    continue
                profile = str(row.get("value_action_candidate_profile", ""))
                flags = str(row.get("value_action_guardrail_flags", ""))
                profile_counter[(date, str(row.get("robust_action_name", "")), profile)] += 1
                flags_counter[(date, flags)] += 1
                action_rows.append(
                    {
                        "seed": seed,
                        "compare_to": reference_endpoint,
                        "date": date,
                        "robust_action_name": str(row.get("robust_action_name", "")),
                        "candidate_profile": profile,
                        "guardrail_flags": flags,
                        "reserve_ratio": float(row.get("value_action_reserve_ratio", 0.0) or 0.0),
                        "flex_ratio": float(row.get("value_action_flex_ratio", 0.0) or 0.0),
                        "release_ratio": float(row.get("value_action_release_ratio", 0.0) or 0.0),
                        "p2_threshold": float(row.get("v6_p2_threshold", 0.0) or 0.0),
                        "planned_today": int(row.get("planned_today", 0) or 0),
                        "delivered_today": int(row.get("delivered_today", 0) or 0),
                        "vrp_dropped": int(row.get("vrp_dropped", 0) or 0),
                        "failures": int(row.get("failures", 0) or 0),
                    }
                )

        summary_rows.append(
            {
                "compare_to": reference_endpoint,
                "extra_fail_count": sum(extra_counter.values()),
                "avoided_fail_count": sum(avoided_counter.values()),
                "net_extra_fail_count": sum(extra_counter.values()) - sum(avoided_counter.values()),
                "extra_fail_by_date": json.dumps(dict(sorted(extra_counter.items())), ensure_ascii=False),
                "avoided_fail_by_date": json.dumps(dict(sorted(avoided_counter.items())), ensure_ascii=False),
                "extra_fail_by_reason": json.dumps(dict(sorted(reason_counter.items())), ensure_ascii=False),
                "extra_fail_by_window_days": json.dumps(dict(sorted(window_counter.items())), ensure_ascii=False),
                "extra_fail_flex_rate": round(sum(extra_flex) / len(extra_flex), 6) if extra_flex else 0.0,
                "extra_fail_mean_demand_colli": round(sum(extra_demand) / len(extra_demand), 6) if extra_demand else 0.0,
                "extra_fail_mean_service_time": round(sum(extra_service) / len(extra_service), 6) if extra_service else 0.0,
                "extra_fail_mean_route_burden": round(sum(extra_route) / len(extra_route), 6) if extra_route else 0.0,
                "top_extra_fail_ids": json.dumps(dict(extra_ids.most_common(10)), ensure_ascii=False),
            }
        )

        lines = [
            f"# Residual Failure Audit: {args.candidate_endpoint} vs {reference_endpoint}",
            "",
            f"- Extra fails: `{sum(extra_counter.values())}`",
            f"- Avoided fails: `{sum(avoided_counter.values())}`",
            f"- Net extra fails: `{sum(extra_counter.values()) - sum(avoided_counter.values())}`",
            f"- Extra fail by date: `{_format_counter(extra_counter)}`",
            f"- Avoided fail by date: `{_format_counter(avoided_counter)}`",
            f"- Extra fail by reason: `{_format_counter(reason_counter)}`",
            f"- Extra fail by delivery_window_days: `{_format_counter(window_counter)}`",
            f"- Extra fail mean demand colli: `{(sum(extra_demand) / len(extra_demand)) if extra_demand else 0.0:.3f}`",
            f"- Extra fail mean service_time: `{(sum(extra_service) / len(extra_service)) if extra_service else 0.0:.3f}`",
            f"- Extra fail mean route burden: `{(sum(extra_route) / len(extra_route)) if extra_route else 0.0:.6f}`",
            f"- Extra fail flex rate: `{(sum(extra_flex) / len(extra_flex)) if extra_flex else 0.0:.3f}`",
            "",
            "## Candidate Action Patterns",
            "",
        ]
        for (date, action_name, profile), count in sorted(profile_counter.items()):
            lines.append(f"- `{date}`: `{action_name}` / `{profile}` seen `{count}` times")
        lines.extend(["", "## Guardrail Flags", ""])
        for (date, flags), count in sorted(flags_counter.items()):
            lines.append(f"- `{date}`: `{flags}` seen `{count}` times")
        report_path = output_dir / f"residual_failure_audit_{reference_endpoint}.md"
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    delta_csv = output_dir / "residual_failure_delta_rows.csv"
    summary_csv = output_dir / "residual_failure_summary.csv"
    action_csv = output_dir / "residual_failure_action_rows.csv"
    _write_csv(
        delta_csv,
        delta_rows,
        [
            "seed",
            "compare_to",
            "delta_kind",
            "id",
            "fail_date",
            "deadline",
            "release_date",
            "reason",
            "delivery_window_days",
            "is_flexible",
            "demand_colli",
            "service_time",
            "route_burden",
        ],
    )
    _write_csv(
        summary_csv,
        summary_rows,
        [
            "compare_to",
            "extra_fail_count",
            "avoided_fail_count",
            "net_extra_fail_count",
            "extra_fail_by_date",
            "avoided_fail_by_date",
            "extra_fail_by_reason",
            "extra_fail_by_window_days",
            "extra_fail_flex_rate",
            "extra_fail_mean_demand_colli",
            "extra_fail_mean_service_time",
            "extra_fail_mean_route_burden",
            "top_extra_fail_ids",
        ],
    )
    _write_csv(
        action_csv,
        action_rows,
        [
            "seed",
            "compare_to",
            "date",
            "robust_action_name",
            "candidate_profile",
            "guardrail_flags",
            "reserve_ratio",
            "flex_ratio",
            "release_ratio",
            "p2_threshold",
            "planned_today",
            "delivered_today",
            "vrp_dropped",
            "failures",
        ],
    )
    print(delta_csv)
    print(summary_csv)
    print(action_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
