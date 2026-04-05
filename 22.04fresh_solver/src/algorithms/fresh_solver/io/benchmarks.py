from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path
from typing import Any, Dict, List

from ..core.models import Instance, MatrixRef, Order, VehicleType, Warehouse


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    if len(value) == 5:
        return time.fromisoformat(value)
    return time.fromisoformat(value[:8])


def load_instance_from_benchmark(benchmark_path: str, matrix_dir: str) -> Instance:
    benchmark_path = str(benchmark_path)
    with open(benchmark_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    raw_orders = data.get("orders", data.get("customers", []))
    orders: List[Order] = []
    for idx, raw in enumerate(raw_orders):
        order_id = str(raw.get("OrderId", raw.get("order_id", idx)))
        depot_id = str(raw.get("Depot", raw.get("depot", metadata.get("depot", "depot"))))
        orders.append(
            Order(
                order_id=order_id,
                depot_id=depot_id,
                requested_date=_parse_date(raw.get("DateRequested", metadata.get("start_date", "2025-01-01"))),
                service_date_from=_parse_date(raw.get("DeliveryDateFrom", metadata.get("start_date", "2025-01-01"))),
                service_date_to=_parse_date(raw.get("DeliveryDateFrom2", metadata.get("end_date", metadata.get("start_date", "2025-01-01")))),
                earliest_time=_parse_time(raw.get("DeliveryEarliestTime", "06:00")),
                latest_time=_parse_time(raw.get("DeliveryLatestTime", "22:00")),
                colli_count=float(raw.get("ColliCount", 0.0)),
                volume=float(raw.get("Volume", 0.0)),
                weight=float(raw.get("Weight", 0.0)),
                delivery_task_time_min=float(raw.get("DeliveryTaskTime", 0.0)),
                picking_task_time_min=float(raw.get("PickingTaskTime", 0.0)),
                customer_node_id=str(raw.get("DeliveryAddress", raw.get("node_id", order_id))),
                metadata=raw,
            )
        )

    depot_id = orders[0].depot_id if orders else str(metadata.get("depot", "depot"))
    warehouses = {
        depot_id: Warehouse(
            depot_id=depot_id,
            earliest_departure=_parse_time("06:00"),
            latest_departure=_parse_time("17:00"),
            picking_open=_parse_time("00:00"),
            picking_close=_parse_time("23:59"),
            gates=10,
            loading_time_min=30.0,
            unloading_time_min=30.0,
            max_staging_space=500.0,
            picking_capacity_colli_per_hour=200.0,
            picking_capacity_volume_per_hour=100.0,
        )
    }
    vehicle_types = [
        VehicleType(
            vehicle_type_id="default_vehicle",
            depot_id=depot_id,
            vehicle_count=50,
            capacity_colli=99999.0,
            capacity_volume=99999.0,
            capacity_weight=99999.0,
            max_route_duration_min=12 * 60.0,
            max_route_distance_km=999.0,
        )
    ]

    start_date = _parse_date(metadata.get("start_date", metadata.get("horizon_start", "2025-01-01")))
    end_date = _parse_date(metadata.get("end_date", metadata.get("horizon_end", metadata.get("start_date", "2025-01-01"))))

    return Instance(
        name=Path(benchmark_path).stem,
        start_date=start_date,
        end_date=end_date,
        orders=orders,
        warehouses=warehouses,
        vehicle_types=vehicle_types,
        matrix_ref=MatrixRef(matrix_dir=matrix_dir, node_count=len(orders) + 1),
        metadata=metadata,
    )
