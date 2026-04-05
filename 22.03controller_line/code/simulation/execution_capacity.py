from __future__ import annotations

from dataclasses import dataclass

from .shock_state import ShockState


def _clip(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


@dataclass(frozen=True)
class ExecutionCapacityEstimate:
    effective_capacity_colli: float
    effective_stop_budget: int
    route_feasibility_score: float
    fragmentation_risk: float
    trip_penalty: float
    compute_bonus: float
    dispersion_penalty: float
    drop_penalty: float


class ExecutionCapacityEstimator:
    def estimate(
        self,
        *,
        shock_state: ShockState,
        compute_limit: int,
    ) -> ExecutionCapacityEstimate:
        compute_bonus = {
            60: 0.00,
            120: 0.05,
            180: 0.10,
            300: 0.16,
        }.get(int(compute_limit), 0.00)

        drop_penalty = _clip(1.0 - 0.40 * float(shock_state.prev_drop_rate), 0.68, 1.00)
        dispersion_penalty = _clip(1.0 - 0.08 * float(shock_state.route_dispersion_index), 0.78, 1.00)
        trip_penalty = 1.00 if int(shock_state.max_trips_per_vehicle) <= 2 else 0.90
        if int(shock_state.max_trips_per_vehicle) > 2 and int(compute_limit) >= 180:
            trip_penalty = 0.94

        route_feasibility_score = _clip(
            drop_penalty * dispersion_penalty * trip_penalty + compute_bonus,
            0.65,
            1.00,
        )

        effective_capacity_colli = float(shock_state.daily_capacity_colli) * route_feasibility_score
        effective_stop_budget = max(
            1,
            int(float(shock_state.visible_today_count) * route_feasibility_score),
        ) if shock_state.visible_today_count > 0 else 0
        fragmentation_risk = _clip(
            0.45 * float(shock_state.prev_drop_rate)
            + 0.30 * float(shock_state.route_dispersion_index)
            + 0.25 * max(0, int(shock_state.max_trips_per_vehicle) - 2),
            0.0,
            1.0,
        )

        return ExecutionCapacityEstimate(
            effective_capacity_colli=float(effective_capacity_colli),
            effective_stop_budget=int(effective_stop_budget),
            route_feasibility_score=float(route_feasibility_score),
            fragmentation_risk=float(fragmentation_risk),
            trip_penalty=float(trip_penalty),
            compute_bonus=float(compute_bonus),
            dispersion_penalty=float(dispersion_penalty),
            drop_penalty=float(drop_penalty),
        )
