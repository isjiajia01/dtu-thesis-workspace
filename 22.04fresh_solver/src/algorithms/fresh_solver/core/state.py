from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Set

from .models import DayState, RepairResult


def build_initial_day_state(planning_date, open_order_ids: Iterable[str]) -> DayState:
    order_ids = list(open_order_ids)
    return DayState(
        planning_date=planning_date,
        open_order_ids=order_ids,
        backlog_order_ids=order_ids.copy(),
    )


def advance_day_state(current_state: DayState, repair_result: RepairResult, deferred_order_ids: Iterable[str]) -> DayState:
    assigned: Set[str] = {
        stop.order_id
        for route in repair_result.repaired_solution.routes
        for stop in route.stops
    }
    deferred = set(deferred_order_ids)
    remaining = [order_id for order_id in current_state.open_order_ids if order_id not in assigned]
    return replace(
        current_state,
        committed_order_ids=list(assigned),
        backlog_order_ids=[order_id for order_id in remaining if order_id in deferred],
        metadata={
            **current_state.metadata,
            "last_depot_penalty": repair_result.diagnostics.depot_penalty,
            "last_overload_bucket_count": repair_result.diagnostics.overload_bucket_count,
        },
    )
