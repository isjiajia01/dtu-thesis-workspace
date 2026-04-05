from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .shock_state import ShockState


@dataclass(frozen=True)
class ControlAction:
    name: str
    event_mode: str | None = None
    lookahead_days: int | None = None
    deadline_guardrail_days: int | None = None
    urgent_hard_days: int | None = None
    buffer_ratio: float | None = None
    reserve_capacity_ratio: float | None = None
    flex_commitment_ratio: float | None = None
    carryover_bonus: float | None = None
    crisis_hard_days: int | None = None
    crisis_hard_days_boost_to: int | None = None
    crisis_routeability_mode: str | None = None
    crisis_routeability_drop_threshold: float | None = None
    crisis_max_stops: int | None = None
    compute_limit: int | None = None
    p2_criticality_threshold: float | None = None
    p3_release_ratio: float | None = None
    risk_budget_epsilon: float | None = None
    effective_capacity_colli: float | None = None
    buffer_capacity_colli: float | None = None
    effective_stop_budget: int | None = None
    fragmentation_risk: float | None = None
    trip_penalty: float | None = None
    route_feasibility_score: float | None = None
    dispersion_penalty: float | None = None
    drop_penalty: float | None = None
    route_intensity_target: str | None = None
    frontier_id: str | None = None
    value_to_go_estimate: float | None = None
    value_model_kind: str | None = None
    candidate_profile: str | None = None
    candidate_profile_penalty: float | None = None
    guardrail_penalty: float | None = None
    guardrail_flags: str | None = None
    execution_guard_level: float | None = None
    execution_penalty_spread: float | None = None
    execution_hard_sort_enabled: bool | None = None
    hard_stop_reservation_enabled: bool | None = None
    hard_stop_reservation_ratio: float | None = None
    hard_capacity_reservation_ratio: float | None = None
    solver_reserved_hard_penalty_multiplier: float | None = None
    committed_order_ids: Tuple[str, ...] | None = None
    buffered_order_ids: Tuple[str, ...] | None = None
    deferred_order_ids: Tuple[str, ...] | None = None

    def to_policy_overrides(self) -> dict[str, object]:
        out: dict[str, object] = {}
        for key in (
            "event_mode",
            "lookahead_days",
            "deadline_guardrail_days",
            "urgent_hard_days",
            "buffer_ratio",
            "reserve_capacity_ratio",
            "flex_commitment_ratio",
            "carryover_bonus",
            "crisis_hard_days",
            "crisis_hard_days_boost_to",
            "crisis_routeability_mode",
            "crisis_routeability_drop_threshold",
            "crisis_max_stops",
            "p2_criticality_threshold",
            "p3_release_ratio",
            "execution_guard_level",
            "execution_penalty_spread",
            "execution_hard_sort_enabled",
            "hard_stop_reservation_enabled",
            "hard_stop_reservation_ratio",
            "hard_capacity_reservation_ratio",
            "solver_reserved_hard_penalty_multiplier",
        ):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        return out


def build_candidate_actions(base_config: dict, shock_state: ShockState, controller_version: str = "v2") -> list[ControlAction]:
    base_lookahead = int(base_config.get("lookahead_days", 3))
    base_guardrail = int(base_config.get("deadline_guardrail_days", 1))
    base_buffer = float(base_config.get("buffer_ratio", 1.05))
    severe_shock = shock_state.capacity_ratio_today < 0.75
    compute_boost = 300 if severe_shock else 120
    base_carryover = float(base_config.get("online_carryover_bonus", 3.0))
    future_tightness = max(0.0, shock_state.backlog_pressure_ratio - 1.0)
    hard_tightness = max(0.0, shock_state.hard_pressure_ratio - 1.0)

    if str(controller_version).lower() == "v3_commitment":
        reserve_base = 0.08 if shock_state.shock_event else 0.04
        return [
            ControlAction(
                name="commit_baseline",
                event_mode="commit_hold",
                lookahead_days=max(base_lookahead, 3),
                deadline_guardrail_days=max(base_guardrail, 1),
                urgent_hard_days=int(base_config.get("urgent_hard_days", 1)),
                buffer_ratio=base_buffer,
                reserve_capacity_ratio=reserve_base,
                flex_commitment_ratio=0.95,
                carryover_bonus=base_carryover,
                crisis_hard_days=int(base_config.get("crisis_hard_days", 2)),
                crisis_hard_days_boost_to=int(base_config.get("crisis_hard_days_boost_to", 3)),
                p2_criticality_threshold=2.8,
                p3_release_ratio=0.0,
                compute_limit=int(base_config.get("base_compute", 60)),
            ),
            ControlAction(
                name="commit_reserve",
                event_mode="commit_shock_triage",
                lookahead_days=max(base_lookahead, 4),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.05),
                reserve_capacity_ratio=0.12 if shock_state.shock_event else 0.08,
                flex_commitment_ratio=0.80,
                carryover_bonus=max(base_carryover, 4.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                p2_criticality_threshold=3.6,
                p3_release_ratio=0.0,
                compute_limit=compute_boost,
            ),
            ControlAction(
                name="commit_triage",
                event_mode="commit_shock_triage",
                lookahead_days=max(base_lookahead, 4),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.05),
                reserve_capacity_ratio=0.16 if shock_state.deadline_spike else 0.12,
                flex_commitment_ratio=0.65,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.05 if shock_state.drop_spike else 0.08,
                p2_criticality_threshold=4.2,
                p3_release_ratio=0.0,
                compute_limit=compute_boost,
            ),
            ControlAction(
                name="commit_recovery_push",
                event_mode="commit_release_buffer",
                lookahead_days=max(base_lookahead, 5),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.08),
                reserve_capacity_ratio=0.05,
                flex_commitment_ratio=1.00,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.08,
                p2_criticality_threshold=2.4,
                p3_release_ratio=0.35,
                compute_limit=compute_boost,
            ),
            ControlAction(
                name="commit_flush_recovery",
                event_mode="commit_flush_recovery",
                lookahead_days=max(base_lookahead, 5),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.08),
                reserve_capacity_ratio=0.02,
                flex_commitment_ratio=1.00,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.10,
                p2_criticality_threshold=1.8,
                p3_release_ratio=1.0,
                compute_limit=compute_boost,
            ),
        ]

    if str(controller_version).lower() == "v4_event_commitment":
        return [
            ControlAction(
                name="commit_hold",
                event_mode="commit_hold",
                lookahead_days=max(base_lookahead, 3),
                deadline_guardrail_days=max(base_guardrail, 1),
                urgent_hard_days=int(base_config.get("urgent_hard_days", 1)),
                buffer_ratio=base_buffer,
                reserve_capacity_ratio=0.12 if shock_state.shock_event else 0.06,
                flex_commitment_ratio=0.65,
                carryover_bonus=max(base_carryover, 4.0),
                crisis_hard_days=int(base_config.get("crisis_hard_days", 2)),
                crisis_hard_days_boost_to=int(base_config.get("crisis_hard_days_boost_to", 3)),
                p2_criticality_threshold=3.8,
                p3_release_ratio=0.0,
                compute_limit=int(base_config.get("base_compute", 60)),
            ),
            ControlAction(
                name="commit_shock_triage",
                event_mode="commit_shock_triage",
                lookahead_days=max(base_lookahead, 4),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.05),
                reserve_capacity_ratio=0.16 if shock_state.drop_spike else 0.12,
                flex_commitment_ratio=0.55,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.05,
                p2_criticality_threshold=4.4,
                p3_release_ratio=0.0,
                compute_limit=compute_boost,
            ),
            ControlAction(
                name="commit_release_buffer",
                event_mode="commit_release_buffer",
                lookahead_days=max(base_lookahead, 5),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.08),
                reserve_capacity_ratio=0.08,
                flex_commitment_ratio=0.90,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.08,
                p2_criticality_threshold=2.8,
                p3_release_ratio=0.40,
                compute_limit=compute_boost,
            ),
            ControlAction(
                name="commit_flush_recovery",
                event_mode="commit_flush_recovery",
                lookahead_days=max(base_lookahead, 5),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.08),
                reserve_capacity_ratio=0.02,
                flex_commitment_ratio=1.00,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.10,
                p2_criticality_threshold=1.8,
                p3_release_ratio=1.0,
                compute_limit=compute_boost,
            ),
        ]

    if str(controller_version).lower() == "v5_risk_budgeted_commitment":
        reserve_lift = min(0.08, 0.03 * future_tightness + 0.04 * hard_tightness + 0.15 * shock_state.prev_drop_rate)
        threshold_lift = 0.6 * future_tightness + 0.8 * hard_tightness
        adaptive_compute = 300 if (severe_shock or shock_state.prev_drop_rate >= 0.08 or hard_tightness >= 0.10) else 180
        return [
            ControlAction(
                name="risk_guard",
                event_mode="commit_hold",
                lookahead_days=max(base_lookahead, 4),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.05),
                reserve_capacity_ratio=min(0.22, 0.10 + reserve_lift),
                flex_commitment_ratio=0.55,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.05,
                p2_criticality_threshold=4.2 + threshold_lift,
                p3_release_ratio=0.0,
                compute_limit=adaptive_compute,
            ),
            ControlAction(
                name="risk_triage",
                event_mode="commit_shock_triage",
                lookahead_days=max(base_lookahead, 5),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.08),
                reserve_capacity_ratio=min(0.24, 0.12 + reserve_lift),
                flex_commitment_ratio=0.45,
                carryover_bonus=max(base_carryover, 6.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.05,
                p2_criticality_threshold=4.8 + threshold_lift,
                p3_release_ratio=0.0,
                compute_limit=adaptive_compute,
            ),
            ControlAction(
                name="risk_rebalance",
                event_mode="commit_release_buffer",
                lookahead_days=max(base_lookahead, 5),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.08),
                reserve_capacity_ratio=max(0.05, min(0.18, 0.08 + 0.5 * reserve_lift)),
                flex_commitment_ratio=0.80,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.08,
                p2_criticality_threshold=3.1 + 0.5 * threshold_lift,
                p3_release_ratio=0.35,
                compute_limit=max(120, adaptive_compute),
            ),
            ControlAction(
                name="risk_flush",
                event_mode="commit_flush_recovery",
                lookahead_days=max(base_lookahead, 6),
                deadline_guardrail_days=max(base_guardrail, 2),
                urgent_hard_days=2,
                buffer_ratio=max(base_buffer, 1.10),
                reserve_capacity_ratio=0.02,
                flex_commitment_ratio=1.00,
                carryover_bonus=max(base_carryover, 5.0),
                crisis_hard_days=3,
                crisis_hard_days_boost_to=4,
                crisis_routeability_mode="drop",
                crisis_routeability_drop_threshold=0.10,
                p2_criticality_threshold=1.8,
                p3_release_ratio=1.0,
                compute_limit=max(120, adaptive_compute),
            ),
        ]

    return [
        ControlAction(
            name="baseline",
            lookahead_days=base_lookahead,
            deadline_guardrail_days=base_guardrail,
            urgent_hard_days=int(base_config.get("urgent_hard_days", 1)),
            buffer_ratio=base_buffer,
            reserve_capacity_ratio=0.0,
            flex_commitment_ratio=1.0,
            carryover_bonus=base_carryover,
            crisis_hard_days=int(base_config.get("crisis_hard_days", 2)),
            crisis_hard_days_boost_to=int(base_config.get("crisis_hard_days_boost_to", 3)),
            compute_limit=int(base_config.get("base_compute", 60)),
        ),
        ControlAction(
            name="deadline_focus",
            lookahead_days=max(base_lookahead, 4),
            deadline_guardrail_days=max(base_guardrail, 2),
            urgent_hard_days=2,
            buffer_ratio=max(base_buffer, 1.05),
            reserve_capacity_ratio=0.0,
            flex_commitment_ratio=1.0,
            carryover_bonus=base_carryover,
            crisis_hard_days=3,
            crisis_hard_days_boost_to=4,
            compute_limit=compute_boost,
        ),
        ControlAction(
            name="routeable_crisis",
            lookahead_days=max(base_lookahead, 4),
            deadline_guardrail_days=max(base_guardrail, 1),
            urgent_hard_days=2,
            buffer_ratio=base_buffer,
            reserve_capacity_ratio=0.0,
            flex_commitment_ratio=1.0,
            carryover_bonus=base_carryover,
            crisis_hard_days=3,
            crisis_hard_days_boost_to=4,
            crisis_routeability_mode="drop",
            crisis_routeability_drop_threshold=0.05,
            compute_limit=compute_boost,
        ),
        ControlAction(
            name="balanced_robust",
            lookahead_days=max(base_lookahead, 5),
            deadline_guardrail_days=max(base_guardrail, 2),
            urgent_hard_days=2,
            buffer_ratio=max(base_buffer, 1.08),
            reserve_capacity_ratio=0.0,
            flex_commitment_ratio=1.0,
            carryover_bonus=base_carryover,
            crisis_hard_days=3,
            crisis_hard_days_boost_to=4,
            crisis_routeability_mode="drop",
            crisis_routeability_drop_threshold=0.08,
            compute_limit=compute_boost,
        ),
    ]
