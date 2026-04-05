from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import hypot


def _days_until(date_str: str | None, current_date: datetime) -> int:
    if not date_str:
        return 999
    try:
        target_dt = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return 999
    return (target_dt - current_date).days


@dataclass(frozen=True)
class ShockState:
    day_index: int
    current_date: str
    capacity_ratio_today: float
    daily_capacity_colli: float
    base_capacity_colli: float
    visible_orders_count: int
    visible_today_count: int
    visible_colli: float
    visible_today_colli: float
    carryover_count: int
    carryover_colli: float
    due_today_count: int
    due_today_colli: float
    due_today_pressure_ratio: float
    due_soon_count: int
    due_soon_colli: float
    due_soon_pressure_ratio: float
    buffer_count: int
    buffer_colli: float
    prev_day_planned: int
    prev_day_vrp_dropped: int
    prev_day_failures: int
    prev_drop_rate: float
    max_trips_per_vehicle: int
    vehicle_count_today: int
    prev_day_compute_limit: int
    prev_day_routes: int
    route_dispersion_index: float
    visible_today_route_burden_mean: float
    mean_days_to_deadline: float
    hard_pressure_ratio: float
    backlog_pressure_ratio: float
    shock_event: bool
    drop_spike: bool
    deadline_spike: bool


class ShockStateBuilder:
    def build(
        self,
        *,
        day_index: int,
        current_date: datetime,
        visible_orders: list[dict],
        prev_planned_ids: set[str] | set[int] | None,
        daily_capacity_colli: float,
        capacity_ratio_today: float,
        prev_day_planned: int | None,
        prev_day_vrp_dropped: int | None,
        prev_day_failures: int | None,
        buffer_order_ids: set[str] | set[int] | None = None,
        max_trips_per_vehicle: int | None = None,
        vehicle_count_today: int | None = None,
        prev_day_compute_limit: int | None = None,
        prev_day_routes: int | None = None,
        depot: dict | None = None,
    ) -> ShockState:
        today_str = current_date.strftime("%Y-%m-%d")
        carryover_ids = set(prev_planned_ids or [])
        buffer_ids = set(buffer_order_ids or [])

        visible_orders_count = len(visible_orders)
        visible_today_count = 0
        visible_colli = 0.0
        visible_today_colli = 0.0
        carryover_count = 0
        carryover_colli = 0.0
        due_today_count = 0
        due_today_colli = 0.0
        due_soon_count = 0
        due_soon_colli = 0.0
        buffer_count = 0
        buffer_colli = 0.0
        deadline_days: list[int] = []
        today_route_burdens: list[float] = []

        for order in visible_orders:
            demand = float(order.get("demand", {}).get("colli", 0.0))
            visible_colli += demand
            oid = order.get("id")
            feasible_dates = order.get("feasible_dates") or []
            deadline = feasible_dates[-1] if feasible_dates else None
            days_left = _days_until(deadline, current_date)
            deadline_days.append(days_left)

            if oid in carryover_ids:
                carryover_count += 1
                carryover_colli += demand
            if oid in buffer_ids:
                buffer_count += 1
                buffer_colli += demand

            if today_str in feasible_dates:
                visible_today_count += 1
                visible_today_colli += demand
                route_burden = _route_burden(order.get("location"), depot.get("location") if isinstance(depot, dict) else None)
                today_route_burdens.append(route_burden)

            if days_left <= 0:
                due_today_count += 1
                due_today_colli += demand
            elif days_left <= 2:
                due_soon_count += 1
                due_soon_colli += demand

        prev_day_planned = int(prev_day_planned or 0)
        prev_day_vrp_dropped = int(prev_day_vrp_dropped or 0)
        prev_day_failures = int(prev_day_failures or 0)
        prev_day_compute_limit = int(prev_day_compute_limit or 60)
        prev_day_routes = int(prev_day_routes or 0)
        max_trips_per_vehicle = int(max_trips_per_vehicle or 2)
        vehicle_count_today = int(vehicle_count_today or 0)
        prev_drop_rate = (
            float(prev_day_vrp_dropped) / float(prev_day_planned)
            if prev_day_planned > 0
            else 0.0
        )
        cap = max(float(daily_capacity_colli), 1.0)
        base_capacity_colli = cap / max(float(capacity_ratio_today), 1e-6)
        route_burden_mean = (
            float(sum(today_route_burdens) / len(today_route_burdens))
            if today_route_burdens
            else 0.0
        )
        route_burden_std = 0.0
        if len(today_route_burdens) >= 2:
            mean_burden = route_burden_mean
            route_burden_std = (
                sum((value - mean_burden) ** 2 for value in today_route_burdens) / len(today_route_burdens)
            ) ** 0.5
        route_dispersion_index = min(
            2.0,
            route_burden_std / max(1.0, route_burden_mean),
        ) if today_route_burdens else 0.0

        return ShockState(
            day_index=int(day_index),
            current_date=today_str,
            capacity_ratio_today=float(capacity_ratio_today),
            daily_capacity_colli=float(daily_capacity_colli),
            base_capacity_colli=float(base_capacity_colli),
            visible_orders_count=int(visible_orders_count),
            visible_today_count=int(visible_today_count),
            visible_colli=float(visible_colli),
            visible_today_colli=float(visible_today_colli),
            carryover_count=int(carryover_count),
            carryover_colli=float(carryover_colli),
            due_today_count=int(due_today_count),
            due_today_colli=float(due_today_colli),
            due_today_pressure_ratio=float(due_today_colli / cap),
            due_soon_count=int(due_soon_count),
            due_soon_colli=float(due_soon_colli),
            due_soon_pressure_ratio=float(due_soon_colli / cap),
            buffer_count=int(buffer_count),
            buffer_colli=float(buffer_colli),
            prev_day_planned=int(prev_day_planned),
            prev_day_vrp_dropped=int(prev_day_vrp_dropped),
            prev_day_failures=int(prev_day_failures),
            prev_drop_rate=float(prev_drop_rate),
            max_trips_per_vehicle=int(max_trips_per_vehicle),
            vehicle_count_today=int(vehicle_count_today),
            prev_day_compute_limit=int(prev_day_compute_limit),
            prev_day_routes=int(prev_day_routes),
            route_dispersion_index=float(route_dispersion_index),
            visible_today_route_burden_mean=float(route_burden_mean),
            mean_days_to_deadline=float(sum(deadline_days) / len(deadline_days)) if deadline_days else 999.0,
            hard_pressure_ratio=float((due_today_colli + due_soon_colli) / cap),
            backlog_pressure_ratio=float((visible_colli + carryover_colli) / cap),
            shock_event=bool(capacity_ratio_today < 0.95 or prev_drop_rate > 0.05 or prev_day_failures > 0),
            drop_spike=bool(prev_drop_rate > 0.08),
            deadline_spike=bool((due_today_colli + due_soon_colli) / cap > 0.85),
        )


def _route_burden(order_loc, depot_loc) -> float:
    if not isinstance(order_loc, (list, tuple)) or len(order_loc) < 2:
        return 0.0
    if not isinstance(depot_loc, (list, tuple)) or len(depot_loc) < 2:
        return 0.0
    return hypot(float(order_loc[0]) - float(depot_loc[0]), float(order_loc[1]) - float(depot_loc[1]))
