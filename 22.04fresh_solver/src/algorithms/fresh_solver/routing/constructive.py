from __future__ import annotations

from datetime import datetime, time
from typing import Dict, Iterable, List

from ..core.config import RoutingConfig
from ..core.models import ControllerDecision, Instance, Order, Route, RoutingSolution, Stop


def _route_start_datetime(planning_date):
    return datetime.combine(planning_date, time(hour=6, minute=0))


def build_routes_for_day(
    planning_date,
    instance: Instance,
    orders_by_id: Dict[str, Order],
    decision: ControllerDecision,
    config: RoutingConfig,
) -> RoutingSolution:
    selected_ids = decision.protected_order_ids + decision.admitted_flex_order_ids
    routes: List[Route] = []

    current_route: Route | None = None
    stop_index = 0
    for idx, order_id in enumerate(selected_ids):
        order = orders_by_id[order_id]
        if current_route is None or len(current_route.order_ids) >= 8:
            current_route = Route(
                route_id=f"{planning_date.isoformat()}_r{len(routes)+1}",
                depot_id=order.depot_id,
                vehicle_type_id=instance.vehicle_types[0].vehicle_type_id if instance.vehicle_types else "vehicle",
                vehicle_index=len(routes),
                trip_index=1 if len(routes) % 2 == 0 else 2,
                order_ids=[],
                departure_time=_route_start_datetime(planning_date),
            )
            routes.append(current_route)
            stop_index = 0

        current_route.order_ids.append(order_id)
        current_route.stops.append(
            Stop(
                order_id=order_id,
                arrival_time=None,
                service_start_time=None,
                departure_time=None,
            )
        )
        stop_index += 1

    return RoutingSolution(planning_date=planning_date, routes=routes, metadata={"selected_order_count": len(selected_ids)})
