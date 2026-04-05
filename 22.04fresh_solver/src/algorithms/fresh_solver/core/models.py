from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional


@dataclass
class Order:
    order_id: str
    depot_id: str
    requested_date: date
    service_date_from: date
    service_date_to: date
    earliest_time: Optional[time]
    latest_time: Optional[time]
    colli_count: float
    volume: float
    weight: float
    delivery_task_time_min: float
    picking_task_time_min: float
    customer_node_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Warehouse:
    depot_id: str
    earliest_departure: time
    latest_departure: time
    picking_open: time
    picking_close: time
    gates: int
    loading_time_min: float
    unloading_time_min: float
    max_staging_space: float
    picking_capacity_colli_per_hour: float
    picking_capacity_volume_per_hour: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VehicleType:
    vehicle_type_id: str
    depot_id: str
    vehicle_count: int
    capacity_colli: float
    capacity_volume: float
    capacity_weight: float
    max_route_duration_min: float
    max_route_distance_km: float
    max_trips_per_day: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatrixRef:
    matrix_dir: str
    node_count: int
    duration_unit: str = "seconds"
    distance_unit: str = "meters"


@dataclass
class Instance:
    name: str
    start_date: date
    end_date: date
    orders: List[Order]
    warehouses: Dict[str, Warehouse]
    vehicle_types: List[VehicleType]
    matrix_ref: MatrixRef
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderScore:
    order_id: str
    total_score: float
    urgency_score: float
    age_score: float
    risk_score: float
    commitment_score: float
    depot_adjustment: float
    tags: List[str] = field(default_factory=list)


@dataclass
class ControllerDecision:
    planning_date: date
    protected_order_ids: List[str]
    admitted_flex_order_ids: List[str]
    deferred_order_ids: List[str]
    order_scores: Dict[str, OrderScore] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Stop:
    order_id: str
    arrival_time: Optional[datetime]
    service_start_time: Optional[datetime]
    departure_time: Optional[datetime]
    load_colli_after: float = 0.0
    load_volume_after: float = 0.0
    load_weight_after: float = 0.0


@dataclass
class Route:
    route_id: str
    depot_id: str
    vehicle_type_id: str
    vehicle_index: int
    trip_index: int
    order_ids: List[str]
    stops: List[Stop] = field(default_factory=list)
    departure_time: Optional[datetime] = None
    return_time: Optional[datetime] = None
    total_distance_km: float = 0.0
    total_duration_min: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnassignedOrder:
    order_id: str
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingSolution:
    planning_date: date
    routes: List[Route]
    unassigned: List[UnassignedOrder] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DepotBucketUsage:
    bucket_start: datetime
    departures: int = 0
    picking_colli: float = 0.0
    picking_volume: float = 0.0
    staging_space: float = 0.0


@dataclass
class DepotDiagnostics:
    planning_date: date
    depot_penalty: float
    overload_bucket_count: int
    worst_bucket_penalty: float
    bucket_usage: Dict[str, List[DepotBucketUsage]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairResult:
    planning_date: date
    repaired_solution: RoutingSolution
    diagnostics: DepotDiagnostics
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DayState:
    planning_date: date
    open_order_ids: List[str]
    committed_order_ids: List[str] = field(default_factory=list)
    previous_assignments: Dict[str, date] = field(default_factory=dict)
    backlog_order_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunSummary:
    instance_name: str
    planning_date: date
    assigned_orders: int
    unassigned_orders: int
    deferred_orders: int
    route_count: int
    trip2_route_count: int
    total_distance_km: float
    total_duration_min: float
    depot_penalty: float
    overload_bucket_count: int
    runtime_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)
