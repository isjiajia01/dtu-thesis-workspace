#!/usr/bin/env python3
"""
Offline replay evaluation for V6 value rerank on frozen V6b2 candidates.
"""

from __future__ import annotations

import argparse
import csv
import json
import io
import sys
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_CODE_DIR = _REPO_ROOT / "code"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

from simulation import policies
from simulation.robust_controller import RobustController
from simulation.rolling_horizon_integrated import OnlineCapacityAnalyzer
from simulation.shock_state import ShockStateBuilder
from src.results_layout import find_endpoint_dir


DEFAULT_RESULTS_DIR = Path("data/results/EXP_EXP01")
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "_analysis_v6_rerank_eval"
DEFAULT_DATA_PATH = Path("data/processed/multiday_benchmark_herlev.json")


def _load_order_map(data_path: Path) -> tuple[dict, dict[int | str, dict]]:
    payload = json.loads(data_path.read_text())
    orders = payload.get("orders", [])
    order_map = {}
    for order in orders:
        order_map[order["id"]] = order
        original_id = order.get("original_id")
        if original_id is not None:
            order_map[original_id] = order
    return payload, order_map


def _infer_max_trips(endpoint: str) -> int:
    return 3 if "mt3" in endpoint else 2


def _build_seed_rows(
    *,
    simulation_path: Path,
    order_map: dict,
    depot: dict,
    controller_version: str,
    model_path: str,
) -> list[dict[str, object]]:
    payload = json.loads(simulation_path.read_text())
    daily_stats = payload.get("daily_stats", [])
    traces = payload.get("vrp_audit_traces", [])
    endpoint = simulation_path.parent.parent.name
    seed = int(simulation_path.parent.name.split("_", 1)[1])
    prev_planned_ids = set()
    carryover_age: dict[str, int] = {}
    rows = []

    controller = RobustController(
        {
            "robust_horizon_days": 3,
            "robust_controller_version": controller_version,
            "v6_value_model_path": model_path,
        }
    )
    builder = ShockStateBuilder()

    for idx, (day_stat, trace) in enumerate(zip(daily_stats, traces)):
        current_date = datetime.strptime(str(trace["date"]), "%Y-%m-%d")
        visible_orders = [order_map[oid] for oid in trace.get("visible_open_order_ids", []) if oid in order_map]
        analyzer = OnlineCapacityAnalyzer(visible_orders, current_date, float(trace.get("daily_capacity_colli", 0.0)))
        shock_state = builder.build(
            day_index=int(trace.get("day_idx", idx)),
            current_date=current_date,
            visible_orders=visible_orders,
            prev_planned_ids=prev_planned_ids,
            daily_capacity_colli=float(trace.get("daily_capacity_colli", 0.0)),
            capacity_ratio_today=float(trace.get("capacity_ratio", 1.0)),
            prev_day_planned=int(daily_stats[idx - 1]["planned_today"]) if idx > 0 else 0,
            prev_day_vrp_dropped=int(daily_stats[idx - 1]["vrp_dropped"]) if idx > 0 else 0,
            prev_day_failures=int(daily_stats[idx - 1]["failures"]) if idx > 0 else 0,
            buffer_order_ids=set(),
            max_trips_per_vehicle=_infer_max_trips(endpoint),
            vehicle_count_today=0,
            prev_day_compute_limit=int(daily_stats[idx - 1]["compute_limit_seconds"]) if idx > 0 else 60,
            prev_day_routes=int(daily_stats[idx - 1]["vrp_routes"]) if idx > 0 else 0,
            depot=depot,
        )
        policy = policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": int(day_stat.get("compute_limit_seconds", 60))})
        with redirect_stdout(io.StringIO()):
            decision = controller.choose_action(
                shock_state=shock_state,
                visible_orders=visible_orders,
                analyzer=analyzer,
                base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": int(day_stat.get("compute_limit_seconds", 60))},
                policy=policy,
                policy_kwargs={
                    "current_date": current_date,
                    "visible_orders": visible_orders,
                    "analyzer": analyzer,
                    "prev_planned_ids": prev_planned_ids,
                    "buffer_order_ids": set(),
                    "carryover_age_map": carryover_age,
                    "daily_capacity_colli": float(trace.get("daily_capacity_colli", 0.0)),
                    "prev_selected_ids": set(),
                    "capacity_ratio_today": float(trace.get("capacity_ratio", 1.0)),
                    "prev_day_planned": int(daily_stats[idx - 1]["planned_today"]) if idx > 0 else 0,
                    "prev_day_vrp_dropped": int(daily_stats[idx - 1]["vrp_dropped"]) if idx > 0 else 0,
                    "depot": depot,
                    "n_vehicles": 0,
                },
            )
        historical_action = str(day_stat.get("robust_action_name", ""))
        selected_action = str(decision.action.name)
        selected_profile = str(getattr(decision.action, "candidate_profile", ""))
        rows.append(
            {
                "endpoint": endpoint,
                "seed": seed,
                "day_index": idx,
                "date": trace["date"],
                "historical_action": historical_action,
                "selected_action": selected_action,
                "selected_profile": selected_profile,
                "agreement": int(historical_action == selected_action),
                "selected_value_hat": float(getattr(decision.action, "value_to_go_estimate", 0.0) or 0.0),
                "selected_guardrail_penalty": float(getattr(decision.action, "guardrail_penalty", 0.0) or 0.0),
                "selected_guardrail_flags": str(getattr(decision.action, "guardrail_flags", "")),
                "selected_release_ratio": float(getattr(decision.action, "p3_release_ratio", 0.0) or 0.0),
                "selected_reserve_ratio": float(getattr(decision.action, "reserve_capacity_ratio", 0.0) or 0.0),
                "pred_failure_cvar": float(decision.failure_risk_cvar),
            }
        )
        delivered = set(trace.get("delivered_order_ids", []))
        planned = set(trace.get("planned_order_ids", []))
        prev_planned_ids = planned - delivered
        next_age = {}
        for oid in prev_planned_ids:
            next_age[str(oid)] = int(carryover_age.get(str(oid), 0)) + 1
        carryover_age = next_age

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline replay evaluation for V6 rerank")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--data-path", default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--endpoints", nargs="*", default=list([
        "scenario1_robust_v5_risk_budgeted",
        "scenario1_robust_v5_risk_budgeted_compute300",
        "scenario1_robust_v5_risk_budgeted_mt3",
        "scenario1_robust_v6b_value_rerank",
        "scenario1_robust_v6b_value_rerank_compute300",
        "scenario1_robust_v6b_value_rerank_mt3_stress",
        "scenario1_robust_v6b1_value_rerank",
        "scenario1_robust_v6b1_value_rerank_compute300",
        "scenario1_robust_v6b1_value_rerank_mt3_stress",
        "scenario1_robust_v6b2_guarded_value_rerank",
        "scenario1_robust_v6b2_guarded_value_rerank_compute300",
        "scenario1_robust_v6b2_guarded_value_rerank_mt3_stress",
    ]))
    parser.add_argument("--valid-seeds", nargs="*", default=["9", "10"])
    parser.add_argument("--controller-version", default="v6b2_guarded_value_rerank")
    parser.add_argument("--model-path", required=True)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _, order_map = _load_order_map(Path(args.data_path))
    sample_payload = json.loads(Path(args.data_path).read_text())
    depot = sample_payload.get("depot", {})

    valid_seeds = {int(seed) for seed in args.valid_seeds}
    rows = []
    for endpoint in args.endpoints:
        endpoint_dir = find_endpoint_dir(results_dir, endpoint)
        for simulation_path in sorted(endpoint_dir.glob("Seed_*/simulation_results.json")):
            seed = int(simulation_path.parent.name.split("_", 1)[1])
            if seed not in valid_seeds:
                continue
            rows.extend(
                _build_seed_rows(
                    simulation_path=simulation_path,
                    order_map=order_map,
                    depot=depot,
                    controller_version=str(args.controller_version),
                    model_path=str(args.model_path),
                )
            )
    if not rows:
        print("No held-out rows found for offline rerank evaluation.")
        return 1

    csv_path = output_dir / "v6_rerank_eval_rows.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    agreement = sum(int(row["agreement"]) for row in rows) / len(rows)
    profiles = Counter(str(row["selected_profile"]) for row in rows)
    actions = Counter(str(row["selected_action"]) for row in rows)
    flush_count = sum(1 for row in rows if "flush" in str(row["selected_action"]))
    stress_rows = [row for row in rows if "mt3" in str(row["endpoint"])]
    summary = {
        "row_count": len(rows),
        "agreement_rate": float(agreement),
        "distinct_profiles": len([k for k in profiles.keys() if k]),
        "profile_counts": dict(profiles),
        "action_counts": dict(actions),
        "flush_selected_count": int(flush_count),
        "stress_row_count": len(stress_rows),
        "stress_mean_pred_failure_cvar": float(sum(float(r["pred_failure_cvar"]) for r in stress_rows) / max(1, len(stress_rows))),
        "csv_path": str(csv_path),
    }
    summary_path = output_dir / "v6_rerank_eval_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(csv_path)
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
