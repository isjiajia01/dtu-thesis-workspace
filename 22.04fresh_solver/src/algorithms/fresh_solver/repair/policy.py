from __future__ import annotations

from datetime import timedelta

from ..core.config import RepairConfig
from ..core.models import RepairResult, RoutingSolution
from .diagnostics import evaluate_depot_profile


def repair_solution(solution: RoutingSolution, config: RepairConfig) -> RepairResult:
    repaired = solution
    diagnostics = evaluate_depot_profile(repaired, config)

    if diagnostics.overload_bucket_count > 0:
        for route in repaired.routes[1::2]:
            if route.departure_time is not None:
                route.departure_time = route.departure_time + timedelta(minutes=config.bucket_minutes)
        diagnostics = evaluate_depot_profile(repaired, config)

    return RepairResult(
        planning_date=solution.planning_date,
        repaired_solution=repaired,
        diagnostics=diagnostics,
        metadata={"repair_applied": True},
    )
