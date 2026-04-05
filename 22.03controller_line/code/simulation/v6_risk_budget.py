from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import hypot

from .execution_capacity import ExecutionCapacityEstimate
from .future_sampler import FutureScenario
from .shock_state import ShockState


def _clip(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


@dataclass(frozen=True)
class V6RiskBudgetPlan:
    frontier_id: str
    epsilon_today: float
    commitment_capacity_colli: float
    buffer_capacity_colli: float
    p2_threshold: float
    release_ratio: float
    guardrail_days: int
    urgent_hard_days: int


class ScenarioRiskBudgeter:
    def build_frontier(
        self,
        *,
        shock_state: ShockState,
        scenarios: list[FutureScenario],
        exec_estimate: ExecutionCapacityEstimate,
    ) -> list[V6RiskBudgetPlan]:
        future_slack = self._future_slack_ratio(shock_state, scenarios)
        slack_risk = max(0.0, -future_slack)
        horizon_exposure = (
            float(shock_state.due_today_count)
            + float(shock_state.due_soon_count)
            + 0.35 * float(shock_state.visible_orders_count)
        )
        compute_credit = 0.35 * float(exec_estimate.compute_bonus)
        epsilon_horizon = 0.02 * horizon_exposure * (1.0 + compute_credit)
        base_reserve = _clip(
            0.08
            + 0.10 * slack_risk
            + 0.08 * float(exec_estimate.fragmentation_risk)
            + 0.12 * float(shock_state.prev_drop_rate),
            0.03,
            0.18,
        )
        base_reserve = max(0.02, base_reserve - 0.12 * float(exec_estimate.compute_bonus))
        release_boost = 0.50 * float(exec_estimate.compute_bonus)

        frontiers: list[tuple[str, float, float, float, int, int]] = [
            ("conservative", 0.24 * epsilon_horizon, base_reserve + 0.03, 0.00 + 0.10 * release_boost, 4.5, 2, 2),
            ("balanced", 0.36 * epsilon_horizon, base_reserve, 0.16 + 0.20 * release_boost, 3.8, 2, 2),
            (
                "recovery_release",
                0.48 * epsilon_horizon,
                max(0.04, base_reserve - 0.03),
                (0.40 if future_slack > 0.0 else 0.22) + 0.25 * release_boost,
                3.1,
                2,
                2,
            ),
        ]
        if future_slack > 0.20 and shock_state.carryover_count > 0:
            frontiers.append(("flush", 0.62 * epsilon_horizon, 0.02, 1.0, 1.8, 2, 2))

        plans: list[V6RiskBudgetPlan] = []
        for frontier_id, epsilon_today, reserve_ratio, release_ratio, p2_threshold, guardrail_days, hard_days in frontiers:
            reserve_ratio = _clip(reserve_ratio, 0.02, 0.24)
            commitment_capacity = float(exec_estimate.effective_capacity_colli) * (1.0 - reserve_ratio)
            buffer_capacity = max(0.0, float(exec_estimate.effective_capacity_colli) - commitment_capacity)
            plans.append(
                V6RiskBudgetPlan(
                    frontier_id=frontier_id,
                    epsilon_today=float(epsilon_today),
                    commitment_capacity_colli=float(commitment_capacity),
                    buffer_capacity_colli=float(buffer_capacity),
                    p2_threshold=float(p2_threshold),
                    release_ratio=float(_clip(release_ratio, 0.0, 1.0)),
                    guardrail_days=int(guardrail_days),
                    urgent_hard_days=int(hard_days),
                )
            )
        return plans

    def _future_slack_ratio(self, shock_state: ShockState, scenarios: list[FutureScenario]) -> float:
        if not scenarios:
            return 0.0
        total = 0.0
        for scenario in scenarios:
            future_capacity = float(shock_state.base_capacity_colli) * sum(scenario.capacity_ratios[1:])
            future_demand = float(shock_state.visible_colli) * 0.20 * sum(scenario.arrival_multipliers[1:])
            total += (future_capacity - future_demand) / max(1.0, float(shock_state.daily_capacity_colli))
        return total / len(scenarios)


class V6OrderRiskScorer:
    def score(
        self,
        *,
        order: dict,
        days_left: int,
        carry_age: float,
        buffered: bool,
        shock_state: ShockState,
        exec_estimate: ExecutionCapacityEstimate,
        scenarios: list[FutureScenario],
        depot: dict | None,
    ) -> float:
        demand = float(order.get("demand", {}).get("colli", 0.0))
        demand_ratio = demand / max(1.0, float(shock_state.daily_capacity_colli))
        route_burden = self._route_burden(order, depot)
        scenario_commitment_score = self._scenario_commitment_score(days_left, shock_state, scenarios)
        return (
            6.0 / (days_left + 1.0)
            + 1.20 * scenario_commitment_score
            + 0.90 * float(carry_age)
            + 0.60 * float(bool(buffered))
            + 1.00 * float(exec_estimate.fragmentation_risk)
            + 0.35 * demand_ratio
            - 0.08 * route_burden
        )

    def _scenario_commitment_score(
        self,
        days_left: int,
        shock_state: ShockState,
        scenarios: list[FutureScenario],
    ) -> float:
        if not scenarios:
            return 0.0
        score = 0.0
        for scenario in scenarios:
            future_capacity = float(shock_state.base_capacity_colli) * sum(scenario.capacity_ratios[1:])
            future_demand = float(shock_state.visible_colli) * 0.20 * sum(scenario.arrival_multipliers[1:])
            if days_left <= 0:
                score += 2.0
            elif days_left <= 2:
                score += 1.0
            if future_demand > future_capacity:
                score += 0.5
            if min(scenario.capacity_ratios) < float(shock_state.capacity_ratio_today):
                score += 0.3
        return score / len(scenarios)

    def _route_burden(self, order: dict, depot: dict | None) -> float:
        if not isinstance(depot, dict):
            return 0.0
        depot_loc = depot.get("location")
        order_loc = order.get("location")
        if not isinstance(order_loc, (list, tuple)) or len(order_loc) < 2:
            return 0.0
        if not isinstance(depot_loc, (list, tuple)) or len(depot_loc) < 2:
            return 0.0
        return hypot(float(order_loc[0]) - float(depot_loc[0]), float(order_loc[1]) - float(depot_loc[1]))


def order_days_left(order: dict, current_date: str) -> int:
    feasible_dates = order.get("feasible_dates") or []
    if not feasible_dates:
        return 999
    deadline = feasible_dates[-1]
    return (datetime.strptime(deadline, "%Y-%m-%d") - datetime.strptime(current_date, "%Y-%m-%d")).days
