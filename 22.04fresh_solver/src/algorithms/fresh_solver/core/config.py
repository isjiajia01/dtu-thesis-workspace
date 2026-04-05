from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ControllerConfig:
    urgency_weight: float = 5.0
    age_weight: float = 1.0
    risk_weight: float = 2.0
    commitment_weight: float = 2.0
    depot_adjustment_weight: float = 2.0
    protected_reserve_ratio: float = 0.20
    flex_admission_cap_ratio: float = 1.00
    stability_penalty: float = 5.0


@dataclass
class RoutingConfig:
    seed_policy: str = "protected_first"
    insertion_policy: str = "regret2"
    trip2_penalty: float = 10.0
    depot_proxy_penalty: float = 2.0
    local_search_budget: int = 100


@dataclass
class RepairConfig:
    bucket_minutes: int = 15
    gate_penalty_weight: float = 100.0
    picking_penalty_weight: float = 50.0
    staging_penalty_weight: float = 50.0
    trip2_penalty_weight: float = 10.0
    move_budget: int = 100
    rollback_budget: int = 10
    refill_budget: int = 10


@dataclass
class SolverConfig:
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    repair: RepairConfig = field(default_factory=RepairConfig)
