from __future__ import annotations

from ..core.models import RepairResult, RunSummary


def summarize_run(instance_name: str, runtime_seconds: float, repair_result: RepairResult, deferred_orders: int) -> RunSummary:
    routes = repair_result.repaired_solution.routes
    assigned_orders = sum(len(route.order_ids) for route in routes)
    trip2_route_count = sum(1 for route in routes if route.trip_index == 2)
    return RunSummary(
        instance_name=instance_name,
        planning_date=repair_result.planning_date,
        assigned_orders=assigned_orders,
        unassigned_orders=len(repair_result.repaired_solution.unassigned),
        deferred_orders=deferred_orders,
        route_count=len(routes),
        trip2_route_count=trip2_route_count,
        total_distance_km=sum(route.total_distance_km for route in routes),
        total_duration_min=sum(route.total_duration_min for route in routes),
        depot_penalty=repair_result.diagnostics.depot_penalty,
        overload_bucket_count=repair_result.diagnostics.overload_bucket_count,
        runtime_seconds=runtime_seconds,
    )
