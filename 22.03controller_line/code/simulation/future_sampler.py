from __future__ import annotations

from dataclasses import dataclass

from .shock_state import ShockState


@dataclass(frozen=True)
class ScenarioBelief:
    shock_persistence: float
    backlog_growth: float
    recovery_strength: float


@dataclass(frozen=True)
class FutureScenario:
    name: str
    capacity_ratios: tuple[float, ...]
    arrival_multipliers: tuple[float, ...]


class FutureSampler:
    def __init__(self, horizon_days: int = 3):
        self.horizon_days = int(max(2, horizon_days))

    def build_belief(self, state: ShockState) -> ScenarioBelief:
        severity = max(0.0, 1.0 - float(state.capacity_ratio_today))
        persistence = min(0.98, 0.35 + 0.9 * severity + 0.7 * state.prev_drop_rate)
        backlog_growth = min(1.4, 0.15 + 0.6 * max(0.0, state.backlog_pressure_ratio - 1.0))
        recovery = max(0.05, 1.0 - 0.7 * persistence)
        return ScenarioBelief(
            shock_persistence=float(persistence),
            backlog_growth=float(backlog_growth),
            recovery_strength=float(recovery),
        )

    def sample(self, state: ShockState, belief: ScenarioBelief) -> list[FutureScenario]:
        current = float(state.capacity_ratio_today)
        persistent_next = max(0.45, current * (1.0 - 0.05 * belief.shock_persistence))
        rebound_next = min(1.0, current + 0.20 * belief.recovery_strength)
        worsening_next = max(0.40, current - 0.08 * belief.shock_persistence)
        final_rebound = min(1.0, rebound_next + 0.25 * belief.recovery_strength)
        stable_arrivals = 1.0 + 0.15 * belief.backlog_growth
        stressed_arrivals = 1.05 + 0.25 * belief.backlog_growth

        return [
            FutureScenario(
                name="persistent_shock",
                capacity_ratios=(current, persistent_next, persistent_next),
                arrival_multipliers=(1.0, stable_arrivals, stable_arrivals),
            ),
            FutureScenario(
                name="partial_rebound",
                capacity_ratios=(current, rebound_next, final_rebound),
                arrival_multipliers=(1.0, stable_arrivals, 1.0),
            ),
            FutureScenario(
                name="worsening_shock",
                capacity_ratios=(current, worsening_next, worsening_next),
                arrival_multipliers=(1.0, stressed_arrivals, stressed_arrivals),
            ),
            FutureScenario(
                name="volatile",
                capacity_ratios=(current, rebound_next, persistent_next),
                arrival_multipliers=(1.0, stressed_arrivals, stable_arrivals),
            ),
        ]
