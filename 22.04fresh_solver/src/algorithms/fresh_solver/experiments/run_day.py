from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

if __package__ in (None, ""):
    package_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(package_root))
    from fresh_solver.controller import make_controller_decision
    from fresh_solver.core.config import SolverConfig
    from fresh_solver.core.state import build_initial_day_state
    from fresh_solver.evaluation import summarize_run
    from fresh_solver.io import load_instance_from_benchmark
    from fresh_solver.repair import repair_solution
    from fresh_solver.routing import build_routes_for_day
else:
    from ..controller import make_controller_decision
    from ..core.config import SolverConfig
    from ..core.state import build_initial_day_state
    from ..evaluation import summarize_run
    from ..io import load_instance_from_benchmark
    from ..repair import repair_solution
    from ..routing import build_routes_for_day


def run_single_day(benchmark_path: str, matrix_dir: str, output_path: str, config: SolverConfig | None = None):
    config = config or SolverConfig()
    instance = load_instance_from_benchmark(benchmark_path, matrix_dir)
    planning_date = instance.start_date
    orders_by_id = {order.order_id: order for order in instance.orders}
    day_state = build_initial_day_state(planning_date, orders_by_id.keys())

    t0 = time.time()
    decision = make_controller_decision(planning_date, instance.orders, day_state, config.controller)
    routing_solution = build_routes_for_day(planning_date, instance, orders_by_id, decision, config.routing)
    repair_result = repair_solution(routing_solution, config.repair)
    runtime = time.time() - t0

    summary = summarize_run(instance.name, runtime, repair_result, deferred_orders=len(decision.deferred_order_ids))
    output = {
        "decision": asdict(decision),
        "routing_solution": asdict(routing_solution),
        "repair_result": asdict(repair_result),
        "summary": asdict(summary),
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    return output


if __name__ == "__main__":
    thesis_root = Path(__file__).resolve().parents[4]
    benchmark = thesis_root / "data/processed/benchmarks/multiday_benchmark_herlev.json"
    matrix_dir = thesis_root / "data/processed/matrices/vrp_matrix_latest"
    output_path = thesis_root / "results/raw_runs/herlev_single_day_baseline.json"
    run_single_day(str(benchmark), str(matrix_dir), str(output_path))
