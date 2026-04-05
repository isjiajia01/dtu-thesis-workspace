from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from .control_actions import ControlAction, build_candidate_actions
from .execution_capacity import ExecutionCapacityEstimator
from .future_sampler import FutureSampler
from .shock_state import ShockState
from .v6_risk_budget import ScenarioRiskBudgeter, V6OrderRiskScorer, order_days_left
from .v6_value_model import V6ValueFeatureBuilder, V6ValueModel


@dataclass(frozen=True)
class RobustDecision:
    action: ControlAction
    action_score: float
    belief_shock_persistence: float
    belief_backlog_growth: float
    belief_recovery_strength: float
    scenario_loss_mean: float
    scenario_loss_cvar: float
    failure_risk_mean: float
    failure_risk_cvar: float
    candidate_count: int = 0
    evaluated_candidate_count: int = 0
    candidate_limit: int = 0


class RobustController:
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.future_sampler = FutureSampler(horizon_days=int(self.config.get("robust_horizon_days", 3)))
        self.controller_version = str(self.config.get("robust_controller_version", "v2")).lower()
        self.execution_capacity_estimator = ExecutionCapacityEstimator()
        self.v6_risk_budgeter = ScenarioRiskBudgeter()
        self.v6_order_risk_scorer = V6OrderRiskScorer()
        self.v6_value_feature_builder = V6ValueFeatureBuilder()
        self.v6_value_model = self._load_v6_value_model()

    def _is_v6a_execaware(self) -> bool:
        return self.controller_version in {"v6a_execaware_dr_mpc", "v6a1_execaware_dr_mpc"}

    def _is_v6b_value_rerank(self) -> bool:
        return self.controller_version == "v6b_value_rerank"

    def _is_v6b1_value_rerank(self) -> bool:
        return self.controller_version == "v6b1_value_rerank"

    def _is_v6b2_guarded_value_rerank(self) -> bool:
        return self.controller_version == "v6b2_guarded_value_rerank"

    def _is_v6b3_diversified_value_rerank(self) -> bool:
        return self.controller_version == "v6b3_diversified_value_rerank"

    def _is_v6e_phase_guarded_value_rerank(self) -> bool:
        return self.controller_version == "v6e_phase_guarded_value_rerank"

    def _is_v6e_recovery_release_value_rerank(self) -> bool:
        return self.controller_version == "v6e_recovery_release_value_rerank"

    def _is_v6f_execution_guard_value_rerank(self) -> bool:
        return self.controller_version == "v6f_execution_guard_value_rerank"

    def _is_v6g_deadline_reservation_value_rerank(self) -> bool:
        return self.controller_version == "v6g_deadline_reservation_value_rerank"

    def _is_v6h_deadline_boost_value_rerank(self) -> bool:
        return self.controller_version == "v6h_deadline_boost_value_rerank"

    def _load_v6_value_model(self) -> V6ValueModel:
        model_path = self.config.get("v6_value_model_path", "data/results/EXP_EXP01/_analysis_v6_value/v6_value_model.json")
        if not model_path:
            return V6ValueModel(model_path=None, fallback_value=0.0)
        path = Path(str(model_path))
        if not path.exists():
            return V6ValueModel(model_path=None, fallback_value=0.0)
        return V6ValueModel(model_path=path, fallback_value=0.0)

    def choose_action(
        self,
        *,
        shock_state: ShockState,
        visible_orders: list[dict],
        analyzer,
        base_config: dict,
        policy,
        policy_kwargs: dict,
    ) -> RobustDecision:
        belief = self.future_sampler.build_belief(shock_state)
        scenarios = self.future_sampler.sample(shock_state, belief)
        buffer_order_ids = set(policy_kwargs.get("buffer_order_ids", set()) or set())
        carryover_age_map = dict(policy_kwargs.get("carryover_age_map", {}) or {})
        depot = policy_kwargs.get("depot")
        if self._is_v6a_execaware():
            candidates = self._build_v6_candidate_actions(
                shock_state=shock_state,
                visible_orders=visible_orders,
                scenarios=scenarios,
                base_config=base_config,
                buffer_order_ids=buffer_order_ids,
                carryover_age_map=carryover_age_map,
                depot=depot,
            )
        elif self._is_v6h_deadline_boost_value_rerank():
            candidates = self._build_v6h_candidate_actions(
                shock_state=shock_state,
                scenarios=scenarios,
                base_config=base_config,
            )
        elif self._is_v6g_deadline_reservation_value_rerank():
            candidates = self._build_v6g_candidate_actions(
                shock_state=shock_state,
                scenarios=scenarios,
                base_config=base_config,
            )
        elif self._is_v6f_execution_guard_value_rerank():
            candidates = self._build_v6f_candidate_actions(
                shock_state=shock_state,
                scenarios=scenarios,
                base_config=base_config,
            )
        elif self._is_v6e_phase_guarded_value_rerank() or self._is_v6e_recovery_release_value_rerank():
            candidates = self._build_v6e_candidate_actions(
                shock_state=shock_state,
                scenarios=scenarios,
                base_config=base_config,
            )
        elif self._is_v6b3_diversified_value_rerank():
            candidates = self._build_v6b3_candidate_actions(
                shock_state=shock_state,
                scenarios=scenarios,
                base_config=base_config,
            )
        elif self._is_v6b2_guarded_value_rerank():
            candidates = self._build_v6b2_candidate_actions(
                shock_state=shock_state,
                scenarios=scenarios,
                base_config=base_config,
            )
        elif self._is_v6b1_value_rerank():
            candidates = self._build_v6b1_candidate_actions(
                shock_state=shock_state,
                scenarios=scenarios,
                base_config=base_config,
            )
        elif self._is_v6b_value_rerank():
            candidates = build_candidate_actions(base_config, shock_state, controller_version="v5_risk_budgeted_commitment")
        else:
            candidates = build_candidate_actions(base_config, shock_state, controller_version=self.controller_version)

        candidate_count = int(len(candidates))
        candidate_limit = int(self.config.get("robust_candidate_limit", 0) or 0)
        if candidate_limit > 0:
            candidates = candidates[:candidate_limit]
        evaluated_candidate_count = int(len(candidates))

        best_action = candidates[0]
        best_score = float("-inf")
        best_mean_loss = 0.0
        best_cvar = 0.0
        best_failure_mean = 0.0
        best_failure_cvar = 0.0
        best_key = None

        for action in candidates:
            if self.controller_version in {"v5_risk_budgeted_commitment", "v6b_value_rerank"}:
                action = self._adapt_v5_action(
                    action=action,
                    shock_state=shock_state,
                    scenarios=scenarios,
                )
            if self._is_v6b_value_rerank() or self._is_v6b1_value_rerank() or self._is_v6b2_guarded_value_rerank() or self._is_v6b3_diversified_value_rerank() or self._is_v6e_phase_guarded_value_rerank() or self._is_v6e_recovery_release_value_rerank() or self._is_v6f_execution_guard_value_rerank() or self._is_v6g_deadline_reservation_value_rerank() or self._is_v6h_deadline_boost_value_rerank():
                action = self._attach_execution_estimate(
                    action=action,
                    shock_state=shock_state,
                )
            if not self._is_v6a_execaware():
                action = self._materialize_commitment_sets(
                    action=action,
                    shock_state=shock_state,
                    visible_orders=visible_orders,
                    scenarios=scenarios,
                    buffer_order_ids=buffer_order_ids,
                    carryover_age_map=carryover_age_map,
                    base_config=base_config,
                    depot=depot,
                )
            selected_orders = policy.select_orders(control_action=action, **policy_kwargs)
            selected_ids = {order.get("id") for order in selected_orders}
            selected_colli = sum(float(order.get("demand", {}).get("colli", 0.0)) for order in selected_orders)
            due_today_colli = 0.0
            due_soon_colli = 0.0
            today = datetime.strptime(shock_state.current_date, "%Y-%m-%d")
            for order in visible_orders:
                if order.get("id") not in selected_ids:
                    continue
                feasible_dates = order.get("feasible_dates") or []
                deadline = feasible_dates[-1] if feasible_dates else None
                if deadline is None:
                    continue
                days_left = (datetime.strptime(deadline, "%Y-%m-%d") - today).days
                demand = float(order.get("demand", {}).get("colli", 0.0))
                if days_left <= 0:
                    due_today_colli += demand
                elif days_left <= 2:
                    due_soon_colli += demand

            if self._is_v6a_execaware():
                effective_capacity = float(action.effective_capacity_colli or shock_state.daily_capacity_colli)
                delivered_today_est = min(selected_colli, effective_capacity)
            else:
                route_bonus = 0.10 if action.crisis_routeability_mode else 0.0
                guardrail_bonus = 0.03 * max(0, (action.deadline_guardrail_days or 1) - 1)
                compute_bonus = 0.05 if (action.compute_limit or 0) >= 120 else 0.0
                route_success = min(
                    0.99,
                    max(
                        0.65,
                        0.92
                        - 0.55 * shock_state.prev_drop_rate
                        - 0.20 * max(0.0, shock_state.capacity_ratio_today < 1.0)
                        + route_bonus
                        + guardrail_bonus
                        + compute_bonus,
                    ),
                )
                delivered_today_est = min(selected_colli, shock_state.daily_capacity_colli * route_success)
            protected_today = due_today_colli + 0.65 * due_soon_colli

            scenario_losses = []
            scenario_failures = []
            for scenario in scenarios:
                future_capacity = shock_state.base_capacity_colli * sum(scenario.capacity_ratios[1:])
                future_inflow = shock_state.visible_colli * 0.20 * sum(scenario.arrival_multipliers[1:])
                remaining_urgent = max(0.0, protected_today - delivered_today_est)
                backlog_after_today = max(0.0, shock_state.visible_colli - delivered_today_est)
                scenario_loss = (
                    remaining_urgent
                    + max(0.0, backlog_after_today + future_inflow - future_capacity)
                    + 0.25 * max(0.0, shock_state.carryover_colli - delivered_today_est)
                )
                scenario_losses.append(float(scenario_loss))
                failure_risk = (
                    1.20 * max(0.0, due_today_colli - delivered_today_est)
                    + 0.85 * max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli))
                    + max(0.0, backlog_after_today + future_inflow - future_capacity)
                )
                scenario_failures.append(float(failure_risk))

            mean_loss = sum(scenario_losses) / len(scenario_losses)
            worst_k = max(1, len(scenario_losses) // 2)
            cvar_loss = sum(sorted(scenario_losses, reverse=True)[:worst_k]) / worst_k
            failure_mean = sum(scenario_failures) / len(scenario_failures)
            failure_cvar = sum(sorted(scenario_failures, reverse=True)[:worst_k]) / worst_k

            if self.controller_version == "v3_commitment":
                reserve_ratio = float(action.reserve_capacity_ratio or 0.0)
                flex_ratio = float(action.flex_commitment_ratio or 1.0)
                key = (
                    -failure_cvar,
                    -failure_mean,
                    -max(0.0, due_today_colli - delivered_today_est),
                    -max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli)),
                    -reserve_ratio,
                    -max(0.0, flex_ratio - 0.85),
                    delivered_today_est,
                    -mean_loss,
                    -cvar_loss,
                )
                score = float(
                    -1500.0 * failure_cvar
                    - 500.0 * failure_mean
                    - 80.0 * max(0.0, due_today_colli - delivered_today_est)
                    - 30.0 * max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli))
                    - 10.0 * reserve_ratio
                    + 0.015 * delivered_today_est
                    - 0.001 * mean_loss
                )
            elif self.controller_version == "v5_risk_budgeted_commitment":
                reserve_ratio = float(action.reserve_capacity_ratio or 0.0)
                flex_ratio = float(action.flex_commitment_ratio or 1.0)
                release_ratio = float(action.p3_release_ratio or 0.0)
                future_slack = self._expected_future_slack_ratio(shock_state, scenarios)
                commitment_gap = max(
                    0.0,
                    selected_colli - shock_state.daily_capacity_colli * (1.0 - reserve_ratio),
                )
                key = (
                    -failure_cvar,
                    -failure_mean,
                    -max(0.0, due_today_colli - delivered_today_est),
                    -max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli)),
                    -commitment_gap,
                    delivered_today_est,
                    future_slack,
                    release_ratio,
                    -mean_loss,
                    -cvar_loss,
                    -reserve_ratio,
                    -max(0.0, flex_ratio - 0.90),
                )
                score = float(
                    -1800.0 * failure_cvar
                    - 650.0 * failure_mean
                    - 100.0 * max(0.0, due_today_colli - delivered_today_est)
                    - 40.0 * max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli))
                    - 30.0 * commitment_gap
                    + 0.020 * delivered_today_est
                    + 12.0 * future_slack
                    + 2.0 * release_ratio
                    - 0.001 * mean_loss
                )
            elif self._is_v6b_value_rerank() or self._is_v6b1_value_rerank() or self._is_v6b2_guarded_value_rerank() or self._is_v6b3_diversified_value_rerank() or self._is_v6e_phase_guarded_value_rerank() or self._is_v6e_recovery_release_value_rerank() or self._is_v6f_execution_guard_value_rerank() or self._is_v6g_deadline_reservation_value_rerank() or self._is_v6h_deadline_boost_value_rerank():
                exec_estimate = self.execution_capacity_estimator.estimate(
                    shock_state=shock_state,
                    compute_limit=int(action.compute_limit or int(self.config.get("base_compute", 60))),
                )
                value_hat = self._estimate_value_to_go(
                    shock_state=shock_state,
                    action=action,
                    exec_estimate=exec_estimate,
                    selected_colli=selected_colli,
                    due_today_colli=due_today_colli,
                    due_soon_colli=due_soon_colli,
                    mean_loss=mean_loss,
                    cvar_loss=cvar_loss,
                    failure_mean=failure_mean,
                    failure_cvar=failure_cvar,
                    daily_capacity_colli=float(policy_kwargs.get("daily_capacity_colli", shock_state.daily_capacity_colli)),
                )
                action = replace(
                    action,
                    value_to_go_estimate=float(value_hat),
                    value_model_kind=str(self.v6_value_model.model_kind),
                )
                reserve_ratio = float(action.reserve_capacity_ratio or 0.0)
                flex_ratio = float(action.flex_commitment_ratio or 1.0)
                guardrail_penalty = float(action.guardrail_penalty or 0.0)
                profile_penalty = float(action.candidate_profile_penalty or 0.0)
                key = (
                    -failure_cvar,
                    -failure_mean,
                    -max(0.0, due_today_colli - delivered_today_est),
                    -max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli)),
                    -value_hat,
                    -profile_penalty,
                    -guardrail_penalty,
                    delivered_today_est,
                    -mean_loss,
                    -cvar_loss,
                    -reserve_ratio,
                    -max(0.0, flex_ratio - 0.90),
                )
                score = float(
                    -1800.0 * failure_cvar
                    - 650.0 * failure_mean
                    - 100.0 * max(0.0, due_today_colli - delivered_today_est)
                    - 40.0 * max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli))
                    - 0.020 * value_hat
                    - profile_penalty
                    - guardrail_penalty
                    + 0.020 * delivered_today_est
                    - 0.001 * mean_loss
                )
            elif self._is_v6a_execaware():
                effective_capacity = float(action.effective_capacity_colli or shock_state.daily_capacity_colli)
                fragmentation_risk = float(action.fragmentation_risk or 0.0)
                effective_gap = max(0.0, selected_colli - effective_capacity)
                key = (
                    -failure_cvar,
                    -failure_mean,
                    -max(0.0, due_today_colli - delivered_today_est),
                    -max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli)),
                    -effective_gap,
                    delivered_today_est,
                    -fragmentation_risk,
                    -mean_loss,
                    -cvar_loss,
                )
                score = float(
                    -1850.0 * failure_cvar
                    - 700.0 * failure_mean
                    - 110.0 * max(0.0, due_today_colli - delivered_today_est)
                    - 45.0 * max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli))
                    - 40.0 * effective_gap
                    - 15.0 * fragmentation_risk
                    + 0.020 * delivered_today_est
                    - 0.001 * mean_loss
                )
            else:
                key = (
                    -failure_cvar,
                    -failure_mean,
                    -max(0.0, due_today_colli - delivered_today_est),
                    -max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli)),
                    delivered_today_est,
                    -mean_loss,
                    -cvar_loss,
                    -5.0 * max(0.0, (action.buffer_ratio or base_config.get("buffer_ratio", 1.05)) - 1.08),
                )
                score = float(
                    -1000.0 * failure_cvar
                    - 300.0 * failure_mean
                    - 50.0 * max(0.0, due_today_colli - delivered_today_est)
                    - 20.0 * max(0.0, due_soon_colli - max(0.0, delivered_today_est - due_today_colli))
                    + 0.01 * delivered_today_est
                    - 0.001 * mean_loss
                )

            choose = False
            if best_key is None or key > best_key:
                choose = True

            if choose:
                best_action = action
                best_score = score
                best_mean_loss = mean_loss
                best_cvar = cvar_loss
                best_failure_mean = failure_mean
                best_failure_cvar = failure_cvar
                best_key = key

        return RobustDecision(
            action=best_action,
            action_score=float(best_score),
            belief_shock_persistence=float(belief.shock_persistence),
            belief_backlog_growth=float(belief.backlog_growth),
            belief_recovery_strength=float(belief.recovery_strength),
            scenario_loss_mean=float(best_mean_loss),
            scenario_loss_cvar=float(best_cvar),
            failure_risk_mean=float(best_failure_mean),
            failure_risk_cvar=float(best_failure_cvar),
            candidate_count=int(candidate_count),
            evaluated_candidate_count=int(evaluated_candidate_count),
            candidate_limit=int(candidate_limit),
        )

    def _attach_execution_estimate(self, *, action: ControlAction, shock_state: ShockState) -> ControlAction:
        exec_estimate = self.execution_capacity_estimator.estimate(
            shock_state=shock_state,
            compute_limit=int(action.compute_limit or int(self.config.get("base_compute", 60))),
        )
        return replace(
            action,
            effective_capacity_colli=float(exec_estimate.effective_capacity_colli),
            buffer_capacity_colli=float(max(0.0, shock_state.daily_capacity_colli - exec_estimate.effective_capacity_colli)),
            effective_stop_budget=int(exec_estimate.effective_stop_budget),
            fragmentation_risk=float(exec_estimate.fragmentation_risk),
            trip_penalty=float(exec_estimate.trip_penalty),
            route_feasibility_score=float(exec_estimate.route_feasibility_score),
            dispersion_penalty=float(exec_estimate.dispersion_penalty),
            drop_penalty=float(exec_estimate.drop_penalty),
        )

    def _build_v6b1_candidate_actions(
        self,
        *,
        shock_state: ShockState,
        scenarios,
        base_config: dict,
    ) -> list[ControlAction]:
        base_actions = build_candidate_actions(base_config, shock_state, controller_version="v5_risk_budgeted_commitment")
        adapted_actions = [
            self._adapt_v5_action(action=action, shock_state=shock_state, scenarios=scenarios)
            for action in base_actions
        ]
        candidates: list[ControlAction] = list(adapted_actions)
        for action in adapted_actions:
            if action.name in {"risk_guard", "risk_triage"}:
                candidates.append(self._make_v6b1_variant(action=action, shock_state=shock_state, profile="exec_protect"))
            if action.name in {"risk_rebalance", "risk_flush"}:
                candidates.append(self._make_v6b1_variant(action=action, shock_state=shock_state, profile="compute_push"))
        dedup: dict[str, ControlAction] = {}
        for action in candidates:
            dedup[action.name] = action
        return list(dedup.values())

    def _build_v6b2_candidate_actions(
        self,
        *,
        shock_state: ShockState,
        scenarios,
        base_config: dict,
    ) -> list[ControlAction]:
        candidates = self._build_v6b1_candidate_actions(
            shock_state=shock_state,
            scenarios=scenarios,
            base_config=base_config,
        )
        guarded: list[ControlAction] = []
        for action in candidates:
            guarded.append(
                self._guard_v6b2_candidate(
                    action=action,
                    shock_state=shock_state,
                    scenarios=scenarios,
                )
            )
        dedup: dict[str, ControlAction] = {}
        for action in guarded:
            dedup[action.name] = action
        return list(dedup.values())

    def _build_v6b3_candidate_actions(
        self,
        *,
        shock_state: ShockState,
        scenarios,
        base_config: dict,
    ) -> list[ControlAction]:
        base_candidates = self._build_v6b2_candidate_actions(
            shock_state=shock_state,
            scenarios=scenarios,
            base_config=base_config,
        )
        diversified: list[ControlAction] = []
        for action in base_candidates:
            diversified.append(self._label_v6b3_base_candidate(action))
            if str(action.name).startswith("risk_guard") or str(action.name).startswith("risk_triage"):
                diversified.append(self._make_v6b3_variant(action=action, profile="carryover_focus"))
                diversified.append(self._make_v6b3_variant(action=action, profile="route_safe"))
            if str(action.name).startswith("risk_rebalance") or str(action.name).startswith("risk_flush"):
                diversified.append(self._make_v6b3_variant(action=action, profile="balanced_release"))
                diversified.append(self._make_v6b3_variant(action=action, profile="release_cap"))
        dedup: dict[str, ControlAction] = {}
        for action in diversified:
            dedup[action.name] = action
        return list(dedup.values())

    def _build_v6e_candidate_actions(
        self,
        *,
        shock_state: ShockState,
        scenarios,
        base_config: dict,
    ) -> list[ControlAction]:
        phase = self._infer_v6e_phase(shock_state, scenarios)
        base_candidates = self._build_v6b3_candidate_actions(
            shock_state=shock_state,
            scenarios=scenarios,
            base_config=base_config,
        )
        candidates: list[ControlAction] = []
        for action in base_candidates:
            candidates.append(
                replace(
                    action,
                    candidate_profile=str(action.candidate_profile or "baseline"),
                )
            )
            if phase == "onset":
                if str(action.name).startswith("risk_guard") or str(action.name).startswith("risk_triage"):
                    candidates.append(self._make_v6e_variant(action=action, phase=phase, profile="onset_buffer"))
                if str(action.name).startswith("risk_rebalance"):
                    candidates.append(self._make_v6e_variant(action=action, phase=phase, profile="onset_hold"))
            elif phase == "sustain":
                if str(action.name).startswith("risk_guard") or str(action.name).startswith("risk_triage"):
                    candidates.append(self._make_v6e_variant(action=action, phase=phase, profile="sustain_route_safe"))
                if str(action.name).startswith("risk_rebalance") or str(action.name).startswith("risk_flush"):
                    candidates.append(self._make_v6e_variant(action=action, phase=phase, profile="sustain_service"))
            elif phase == "recovery":
                if str(action.name).startswith("risk_rebalance") or str(action.name).startswith("risk_flush"):
                    candidates.append(self._make_v6e_variant(action=action, phase=phase, profile="recovery_drain"))
                    if self._is_v6e_recovery_release_value_rerank():
                        candidates.append(self._make_v6e_variant(action=action, phase=phase, profile="recovery_release_fix"))

        guarded: list[ControlAction] = []
        for action in candidates:
            guarded.append(
                self._guard_v6e_candidate(
                    action=action,
                    phase=phase,
                    shock_state=shock_state,
                    scenarios=scenarios,
                )
            )
        dedup: dict[str, ControlAction] = {}
        for action in guarded:
            dedup[action.name] = action
        return list(dedup.values())

    def _build_v6f_candidate_actions(
        self,
        *,
        shock_state: ShockState,
        scenarios,
        base_config: dict,
    ) -> list[ControlAction]:
        base_candidates = self._build_v6b2_candidate_actions(
            shock_state=shock_state,
            scenarios=scenarios,
            base_config=base_config,
        )
        guarded: list[ControlAction] = []
        for action in base_candidates:
            guarded.append(
                self._apply_v6f_execution_guard(
                    action=action,
                    shock_state=shock_state,
                    scenarios=scenarios,
                )
            )
        dedup: dict[str, ControlAction] = {}
        for action in guarded:
            dedup[action.name] = action
        return list(dedup.values())

    def _build_v6g_candidate_actions(
        self,
        *,
        shock_state: ShockState,
        scenarios,
        base_config: dict,
    ) -> list[ControlAction]:
        base_candidates = self._build_v6f_candidate_actions(
            shock_state=shock_state,
            scenarios=scenarios,
            base_config=base_config,
        )
        narrowed: list[ControlAction] = []
        for action in base_candidates:
            narrowed.append(
                self._apply_v6g_deadline_reservation(
                    action=action,
                    shock_state=shock_state,
                    scenarios=scenarios,
                )
            )
        dedup: dict[str, ControlAction] = {}
        for action in narrowed:
            dedup[action.name] = action
        return list(dedup.values())

    def _build_v6h_candidate_actions(
        self,
        *,
        shock_state: ShockState,
        scenarios,
        base_config: dict,
    ) -> list[ControlAction]:
        base_candidates = self._build_v6g_candidate_actions(
            shock_state=shock_state,
            scenarios=scenarios,
            base_config=base_config,
        )
        boosted: list[ControlAction] = []
        for action in base_candidates:
            boosted.append(self._apply_v6h_deadline_boost(action=action, shock_state=shock_state))
        dedup: dict[str, ControlAction] = {}
        for action in boosted:
            dedup[action.name] = action
        return list(dedup.values())

    def _infer_v6e_phase(self, shock_state: ShockState, scenarios) -> str:
        severe_shock = float(shock_state.capacity_ratio_today) <= 0.70
        sustained_damage = float(shock_state.prev_drop_rate) >= 0.05 or int(shock_state.prev_day_failures) > 0
        backlog_heavy = float(shock_state.carryover_colli) >= 0.40 * max(1.0, float(shock_state.daily_capacity_colli))
        future_slack = self._expected_future_slack_ratio(shock_state, scenarios)
        if self._is_v6e_recovery_release_value_rerank():
            routing_stabilized = float(shock_state.prev_drop_rate) <= 0.12 and float(shock_state.route_dispersion_index) <= 0.35
            recovery_signal = future_slack >= -0.10 and int(shock_state.prev_day_failures) <= 8
            if severe_shock and sustained_damage and routing_stabilized and recovery_signal:
                return "recovery"
        if severe_shock and not sustained_damage:
            return "onset"
        if severe_shock:
            return "sustain"
        if sustained_damage or backlog_heavy:
            return "recovery"
        return "baseline"

    def _apply_v6f_execution_guard(
        self,
        *,
        action: ControlAction,
        shock_state: ShockState,
        scenarios,
    ) -> ControlAction:
        future_slack = self._expected_future_slack_ratio(shock_state, scenarios)
        frag = float(shock_state.prev_drop_rate) + 0.5 * float(shock_state.route_dispersion_index)
        hard_pressure = float(shock_state.hard_pressure_ratio)
        execution_guard_level = min(
            1.0,
            max(
                0.20,
                0.35
                + 1.20 * float(shock_state.prev_drop_rate)
                + 0.45 * float(shock_state.route_dispersion_index)
                + 0.25 * max(0.0, hard_pressure - 0.80)
                + 0.15 * max(0.0, -future_slack),
            ),
        )
        execution_penalty_spread = min(0.30, 0.10 + 0.10 * frag + 0.06 * max(0.0, hard_pressure - 0.80))
        profile = str(action.candidate_profile or "baseline")
        penalty = float(action.candidate_profile_penalty or 0.0)
        if "compute_push" in profile and frag >= 0.18:
            penalty += 40.0
            execution_guard_level = min(1.0, execution_guard_level + 0.10)
        return replace(
            action,
            execution_guard_level=float(execution_guard_level),
            execution_penalty_spread=float(execution_penalty_spread),
            execution_hard_sort_enabled=True,
            candidate_profile=f"{profile}|exec_guard",
            candidate_profile_penalty=float(penalty),
        )

    def _apply_v6g_deadline_reservation(
        self,
        *,
        action: ControlAction,
        shock_state: ShockState,
        scenarios,
    ) -> ControlAction:
        future_slack = self._expected_future_slack_ratio(shock_state, scenarios)
        frag = float(shock_state.prev_drop_rate) + 0.5 * float(shock_state.route_dispersion_index)
        hard_pressure = float(shock_state.hard_pressure_ratio)
        stop_ratio = min(
            0.18,
            max(
                0.08,
                0.08
                + 0.10 * max(0.0, hard_pressure - 0.60)
                + 0.08 * float(shock_state.prev_drop_rate)
                + 0.04 * max(0.0, -future_slack),
            ),
        )
        capacity_ratio = min(
            0.16,
            max(
                0.06,
                0.06
                + 0.08 * max(0.0, hard_pressure - 0.60)
                + 0.05 * frag,
            ),
        )
        penalty = float(action.candidate_profile_penalty or 0.0)
        return replace(
            action,
            hard_stop_reservation_enabled=True,
            hard_stop_reservation_ratio=float(stop_ratio),
            hard_capacity_reservation_ratio=float(capacity_ratio),
            candidate_profile=f"{str(action.candidate_profile or 'baseline')}|hard_res",
            candidate_profile_penalty=float(penalty),
        )

    def _apply_v6h_deadline_boost(
        self,
        *,
        action: ControlAction,
        shock_state: ShockState,
    ) -> ControlAction:
        hard_pressure = float(shock_state.hard_pressure_ratio)
        prev_drop = float(shock_state.prev_drop_rate)
        multiplier = min(
            5.0,
            max(
                2.0,
                2.0
                + 2.0 * max(0.0, hard_pressure - 0.60)
                + 3.0 * prev_drop,
            ),
        )
        return replace(
            action,
            solver_reserved_hard_penalty_multiplier=float(multiplier),
            candidate_profile=f"{str(action.candidate_profile or 'baseline')}|solver_boost",
        )

    def _label_v6b3_base_candidate(self, action: ControlAction) -> ControlAction:
        profile = str(action.candidate_profile or "baseline")
        penalty = 0.0
        if "compute_push" in profile:
            penalty = 60.0
        return replace(action, candidate_profile=profile, candidate_profile_penalty=float(penalty))

    def _make_v6b3_variant(self, *, action: ControlAction, profile: str) -> ControlAction:
        reserve = float(action.reserve_capacity_ratio or 0.0)
        flex = float(action.flex_commitment_ratio or 1.0)
        release = float(action.p3_release_ratio or 0.0)
        p2 = float(action.p2_criticality_threshold or 2.5)
        carry = float(action.carryover_bonus or self.config.get("online_carryover_bonus", 3.0))
        route_target = str(action.route_intensity_target or "normal")
        penalty = 15.0
        if profile == "carryover_focus":
            reserve = min(0.18, reserve + 0.02)
            flex = max(0.50, flex - 0.02)
            release = min(0.40, max(0.12, release))
            p2 = max(1.8, p2 - 0.10)
            carry = carry + 2.0
            route_target = "elevated"
            penalty = 10.0
        elif profile == "route_safe":
            reserve = min(0.20, reserve + 0.04)
            flex = max(0.45, flex - 0.05)
            release = min(0.20, release)
            p2 = p2 + 0.30
            route_target = "normal"
            penalty = 12.0
        elif profile == "balanced_release":
            reserve = min(0.12, max(0.03, reserve))
            flex = min(0.95, flex + 0.03)
            release = min(0.65, max(0.30, release))
            p2 = max(1.7, p2 - 0.20)
            route_target = "elevated"
            penalty = 20.0
        elif profile == "release_cap":
            reserve = min(0.10, max(0.02, reserve + 0.01))
            flex = min(0.90, max(0.55, flex))
            release = min(0.45, release if release > 0 else 0.35)
            p2 = max(1.8, p2 - 0.05)
            route_target = "normal"
            penalty = 18.0
        return replace(
            action,
            name=f"{action.name}_{profile}",
            reserve_capacity_ratio=float(reserve),
            flex_commitment_ratio=float(flex),
            p3_release_ratio=float(release),
            p2_criticality_threshold=float(p2),
            carryover_bonus=float(carry),
            route_intensity_target=route_target,
            candidate_profile=profile,
            candidate_profile_penalty=float(penalty),
        )

    def _make_v6e_variant(self, *, action: ControlAction, phase: str, profile: str) -> ControlAction:
        reserve = float(action.reserve_capacity_ratio or 0.0)
        flex = float(action.flex_commitment_ratio or 1.0)
        release = float(action.p3_release_ratio or 0.0)
        p2 = float(action.p2_criticality_threshold or 2.5)
        carry = float(action.carryover_bonus or self.config.get("online_carryover_bonus", 3.0))
        route_target = str(action.route_intensity_target or "normal")
        penalty = 10.0
        if profile == "onset_buffer":
            reserve = min(0.24, reserve + 0.05)
            flex = max(0.35, flex - 0.08)
            release = min(0.12, release)
            p2 = p2 + 0.50
            carry = carry + 1.5
            route_target = "normal"
            penalty = 8.0
        elif profile == "onset_hold":
            reserve = min(0.20, reserve + 0.04)
            flex = max(0.45, flex - 0.05)
            release = min(0.18, release)
            p2 = p2 + 0.35
            carry = carry + 1.0
            route_target = "elevated"
            penalty = 10.0
        elif profile == "sustain_route_safe":
            reserve = min(0.22, reserve + 0.02)
            flex = max(0.42, flex - 0.04)
            release = min(0.20, release)
            p2 = p2 + 0.20
            carry = carry + 1.0
            route_target = "normal"
            penalty = 11.0
        elif profile == "sustain_service":
            reserve = min(0.14, max(0.03, reserve))
            flex = min(0.92, flex + 0.04)
            release = min(0.35, max(0.15, release))
            p2 = max(1.7, p2 - 0.10)
            carry = carry + 0.5
            route_target = "elevated"
            penalty = 12.0
        elif profile == "recovery_drain":
            reserve = max(0.01, reserve - 0.03)
            flex = min(1.0, flex + 0.06)
            release = min(0.70, max(0.35, release))
            p2 = max(1.5, p2 - 0.25)
            carry = carry + 0.5
            route_target = "max" if (action.compute_limit or 0) >= 180 else "elevated"
            penalty = 14.0
        elif profile == "recovery_release_fix":
            reserve = max(0.01, reserve - 0.02)
            flex = min(1.0, max(0.97, flex + 0.04))
            release = min(0.75, max(0.45, release + 0.10))
            p2 = max(1.6, p2 - 0.15)
            carry = carry + 0.5
            route_target = "max" if (action.compute_limit or 0) >= 180 else "elevated"
            penalty = 7.0
        return replace(
            action,
            name=f"{action.name}_{phase}_{profile}",
            reserve_capacity_ratio=float(reserve),
            flex_commitment_ratio=float(flex),
            p3_release_ratio=float(release),
            p2_criticality_threshold=float(p2),
            carryover_bonus=float(carry),
            route_intensity_target=route_target,
            candidate_profile=profile,
            candidate_profile_penalty=float(penalty),
        )

    def _guard_v6b2_candidate(
        self,
        *,
        action: ControlAction,
        shock_state: ShockState,
        scenarios,
    ) -> ControlAction:
        future_slack = self._expected_future_slack_ratio(shock_state, scenarios)
        frag = float(shock_state.max_trips_per_vehicle > 2) * 0.10 + float(shock_state.prev_drop_rate) + 0.5 * float(shock_state.route_dispersion_index)
        frag = max(frag, 0.0)
        flags: list[str] = []
        penalty = 0.0
        profile = str(action.candidate_profile or "")
        release_ratio = float(action.p3_release_ratio or 0.0)
        reserve_ratio = float(action.reserve_capacity_ratio or 0.0)
        flex_ratio = float(action.flex_commitment_ratio or 1.0)
        threshold = float(action.p2_criticality_threshold or 2.5)

        high_due = float(shock_state.hard_pressure_ratio) >= 0.95 or float(shock_state.due_today_pressure_ratio) >= 0.20
        high_frag = (float(shock_state.max_trips_per_vehicle) > 2 and frag >= 0.22) or frag >= 0.28
        low_slack = future_slack <= 0.05

        if profile == "compute_push":
            if low_slack:
                flags.append("low_slack")
                penalty += 400.0
            if high_due:
                flags.append("high_due")
                penalty += 700.0
            if high_frag:
                flags.append("high_frag")
                penalty += 900.0

            if flags:
                reserve_ratio = min(0.18, reserve_ratio + 0.05)
                flex_ratio = max(0.45, flex_ratio - 0.06)
                threshold = threshold + 0.45
                release_ratio = min(release_ratio, 0.35 if not high_frag else 0.20)
                return replace(
                    action,
                    name=f"{action.name}_guarded",
                    reserve_capacity_ratio=float(reserve_ratio),
                    flex_commitment_ratio=float(flex_ratio),
                    p2_criticality_threshold=float(threshold),
                    p3_release_ratio=float(release_ratio),
                    candidate_profile="guarded",
                    route_intensity_target="elevated" if (action.compute_limit or 0) >= 180 else "normal",
                    guardrail_penalty=float(penalty),
                    guardrail_flags=",".join(flags),
                )
        if str(action.name).startswith("risk_flush") and (high_due or low_slack):
            flags.extend(["flush_guard", "high_due" if high_due else "low_slack"])
            penalty += 600.0 if high_due else 350.0
        return replace(
            action,
            guardrail_penalty=float(penalty),
            guardrail_flags=",".join(flags),
        )

    def _guard_v6e_candidate(
        self,
        *,
        action: ControlAction,
        phase: str,
        shock_state: ShockState,
        scenarios,
    ) -> ControlAction:
        future_slack = self._expected_future_slack_ratio(shock_state, scenarios)
        frag = float(shock_state.prev_drop_rate) + 0.5 * float(shock_state.route_dispersion_index)
        carryover_pressure = float(shock_state.carryover_colli) / max(1.0, float(shock_state.daily_capacity_colli))
        penalty = float(action.guardrail_penalty or 0.0)
        flags = [flag for flag in str(action.guardrail_flags or "").split(",") if flag]
        release_ratio = float(action.p3_release_ratio or 0.0)
        reserve_ratio = float(action.reserve_capacity_ratio or 0.0)
        flex_ratio = float(action.flex_commitment_ratio or 1.0)
        threshold = float(action.p2_criticality_threshold or 2.5)
        profile = str(action.candidate_profile or "")

        if phase == "onset":
            if release_ratio > 0.18:
                flags.append("onset_release_cap")
                penalty += 500.0
                release_ratio = 0.18
            if reserve_ratio < 0.10:
                flags.append("onset_reserve_floor")
                penalty += 250.0
                reserve_ratio = 0.10
            if "balanced_release" in profile or "compute_push" in profile:
                flags.append("onset_aggressive")
                penalty += 600.0
        elif phase == "sustain":
            if future_slack <= 0.05 and release_ratio > 0.30:
                flags.append("sustain_release_cap")
                penalty += 350.0
                release_ratio = 0.30
            if frag >= 0.18 and flex_ratio > 0.90:
                flags.append("sustain_flex_cap")
                penalty += 180.0
                flex_ratio = 0.90
            if reserve_ratio > 0.18 and carryover_pressure > 0.35:
                flags.append("sustain_overreserve")
                penalty += 220.0
        elif phase == "recovery":
            if future_slack > 0.10 and carryover_pressure > 0.25 and release_ratio < 0.25:
                flags.append("recovery_under_release")
                penalty += 260.0
                release_ratio = 0.25
            if reserve_ratio > 0.16:
                flags.append("recovery_overreserve")
                penalty += 220.0
                reserve_ratio = 0.16
            if threshold > 4.6:
                flags.append("recovery_overtriage")
                penalty += 180.0
                threshold = 4.6
            if self._is_v6e_recovery_release_value_rerank():
                if future_slack >= -0.10 and carryover_pressure >= 0.18 and release_ratio < 0.40:
                    flags.append("recovery_release_floor_fix")
                    release_ratio = 0.40
                if reserve_ratio > 0.10:
                    flags.append("recovery_reserve_cap_fix")
                    reserve_ratio = 0.10
                if flex_ratio < 0.97:
                    flags.append("recovery_flex_restore")
                    flex_ratio = 0.97

        return replace(
            action,
            reserve_capacity_ratio=float(reserve_ratio),
            flex_commitment_ratio=float(flex_ratio),
            p2_criticality_threshold=float(threshold),
            p3_release_ratio=float(release_ratio),
            guardrail_penalty=float(penalty),
            guardrail_flags=",".join(flags),
        )


    def _make_v6b1_variant(
        self,
        *,
        action: ControlAction,
        shock_state: ShockState,
        profile: str,
    ) -> ControlAction:
        exec_estimate = self.execution_capacity_estimator.estimate(
            shock_state=shock_state,
            compute_limit=int(action.compute_limit or int(self.config.get("base_compute", 60))),
        )
        reserve = float(action.reserve_capacity_ratio or 0.0)
        flex = float(action.flex_commitment_ratio or 1.0)
        release = float(action.p3_release_ratio or 0.0)
        p2 = float(action.p2_criticality_threshold or 2.5)
        compute_bonus = float(exec_estimate.compute_bonus)
        frag = float(exec_estimate.fragmentation_risk)
        if profile == "exec_protect":
            reserve = min(0.24, reserve + 0.02 + 0.08 * frag)
            flex = max(0.35, flex - 0.08)
            p2 = p2 + 0.45 + 0.40 * frag
            release = max(0.0, release - 0.12)
            route_target = "normal"
        else:
            reserve = max(0.01, reserve - (0.02 + 0.10 * compute_bonus))
            flex = min(1.0, flex + 0.08)
            p2 = max(1.4, p2 - (0.40 + 0.40 * compute_bonus))
            release = min(1.0, release + 0.18 + 0.40 * compute_bonus - 0.10 * frag)
            route_target = "max" if (action.compute_limit or 0) >= 180 else "elevated"
        return replace(
            action,
            name=f"{action.name}_{profile}",
            reserve_capacity_ratio=float(reserve),
            flex_commitment_ratio=float(flex),
            p2_criticality_threshold=float(p2),
            p3_release_ratio=float(release),
            route_intensity_target=route_target,
            candidate_profile=profile,
        )

    def _estimate_value_to_go(
        self,
        *,
        shock_state: ShockState,
        action: ControlAction,
        exec_estimate,
        selected_colli: float,
        due_today_colli: float,
        due_soon_colli: float,
        mean_loss: float,
        cvar_loss: float,
        failure_mean: float,
        failure_cvar: float,
        daily_capacity_colli: float,
    ) -> float:
        feature_row = {
            "capacity_ratio": float(shock_state.capacity_ratio_today),
            "capacity": float(daily_capacity_colli),
            "visible_open_orders": float(shock_state.visible_orders_count),
            "visible_due_today_count": float(shock_state.due_today_count),
            "visible_due_soon_count": float(shock_state.due_soon_count),
            "planned_today": float(len(getattr(action, "committed_order_ids", ()) or ()) + len(getattr(action, "buffered_order_ids", ()) or ())),
            "delivered_today": float(min(selected_colli, float(exec_estimate.effective_capacity_colli))),
            "vrp_dropped": float(shock_state.prev_day_vrp_dropped),
            "compute_limit_seconds": float(action.compute_limit or self.config.get("base_compute", 60)),
            "robust_scenario_loss_mean": float(mean_loss),
            "robust_scenario_loss_cvar": float(cvar_loss),
            "exec_effective_capacity_colli": float(exec_estimate.effective_capacity_colli),
            "exec_effective_capacity_ratio": float(exec_estimate.effective_capacity_colli / max(1.0, daily_capacity_colli)),
            "exec_effective_stop_budget": float(exec_estimate.effective_stop_budget),
            "exec_route_feasibility_score": float(exec_estimate.route_feasibility_score),
            "exec_fragmentation_risk": float(exec_estimate.fragmentation_risk),
            "exec_trip_penalty": float(exec_estimate.trip_penalty),
            "exec_route_dispersion_index": float(shock_state.route_dispersion_index),
            "v6_risk_budget_epsilon": float(action.risk_budget_epsilon or 0.0),
            "v6_commitment_capacity_colli": float(
                (action.effective_capacity_colli or exec_estimate.effective_capacity_colli)
                - float(action.buffer_capacity_colli or 0.0)
            ),
            "v6_buffer_capacity_colli": float(action.buffer_capacity_colli or 0.0),
            "v6_commit_count": float(len(getattr(action, "committed_order_ids", ()) or ())),
            "v6_buffer_count": float(len(getattr(action, "buffered_order_ids", ()) or ())),
            "v6_defer_count": float(len(getattr(action, "deferred_order_ids", ()) or ())),
            "v6_p2_threshold": float(action.p2_criticality_threshold or 0.0),
            "v6_release_ratio": float(action.p3_release_ratio or 0.0),
            "v6_pred_failure_mean": float(failure_mean),
            "v6_pred_failure_cvar": float(failure_cvar),
            "v6_pred_penalized_cost_proxy": float(mean_loss),
            "v6_selected_colli": float(selected_colli),
            "v6_selected_due_today_colli": float(due_today_colli),
            "v6_selected_due_soon_colli": float(due_soon_colli),
            "value_action_reserve_ratio": float(action.reserve_capacity_ratio or 0.0),
            "value_action_flex_ratio": float(action.flex_commitment_ratio or 0.0),
            "value_action_release_ratio": float(action.p3_release_ratio or 0.0),
            "value_action_compute_limit": float(action.compute_limit or self.config.get("base_compute", 60)),
            "value_action_effective_capacity_ratio": float(exec_estimate.effective_capacity_colli / max(1.0, daily_capacity_colli)),
            "value_action_fragmentation_risk": float(exec_estimate.fragmentation_risk),
            "value_action_trip_penalty": float(exec_estimate.trip_penalty),
            "value_action_route_feasibility_score": float(exec_estimate.route_feasibility_score),
            "value_action_commit_count": float(len(getattr(action, "committed_order_ids", ()) or ())),
            "value_action_buffer_count": float(len(getattr(action, "buffered_order_ids", ()) or ())),
            "value_action_defer_count": float(len(getattr(action, "deferred_order_ids", ()) or ())),
        }
        features = self.v6_value_feature_builder.build_from_daily_stat(feature_row)
        return float(self.v6_value_model.predict(features))

    def _build_v6_candidate_actions(
        self,
        *,
        shock_state: ShockState,
        visible_orders: list[dict],
        scenarios,
        base_config: dict,
        buffer_order_ids: set[str],
        carryover_age_map: dict[str, int],
        depot,
    ) -> list[ControlAction]:
        assumed_compute_limit = int(base_config.get("base_compute", 60))
        exec_estimate = self.execution_capacity_estimator.estimate(
            shock_state=shock_state,
            compute_limit=assumed_compute_limit,
        )
        frontier = self.v6_risk_budgeter.build_frontier(
            shock_state=shock_state,
            scenarios=scenarios,
            exec_estimate=exec_estimate,
        )
        actions: list[ControlAction] = []
        for plan in frontier:
            actions.append(
                self._materialize_v6_action(
                    plan=plan,
                    shock_state=shock_state,
                    visible_orders=visible_orders,
                    scenarios=scenarios,
                    exec_estimate=exec_estimate,
                    buffer_order_ids=buffer_order_ids,
                    carryover_age_map=carryover_age_map,
                    depot=depot,
                    compute_limit=assumed_compute_limit,
                )
            )
        return actions

    def _materialize_v6_action(
        self,
        *,
        plan,
        shock_state: ShockState,
        visible_orders: list[dict],
        scenarios,
        exec_estimate,
        buffer_order_ids: set[str],
        carryover_age_map: dict[str, int],
        depot,
        compute_limit: int,
    ) -> ControlAction:
        scored = []
        for order in visible_orders:
            oid = str(order.get("id"))
            feasible_dates = order.get("feasible_dates") or []
            if shock_state.current_date not in feasible_dates:
                continue
            days_left = order_days_left(order, shock_state.current_date)
            carry_age = float(carryover_age_map.get(oid, 0))
            buffered = oid in buffer_order_ids
            risk_score = self.v6_order_risk_scorer.score(
                order=order,
                days_left=days_left,
                carry_age=carry_age,
                buffered=buffered,
                shock_state=shock_state,
                exec_estimate=exec_estimate,
                scenarios=scenarios,
                depot=depot,
            )
            route_penalty = self._route_burden_penalty(order, depot)
            pclass = "P3"
            if days_left <= int(plan.guardrail_days):
                pclass = "P1"
            elif risk_score >= float(plan.p2_threshold):
                pclass = "P2"
            demand = float(order.get("demand", {}).get("colli", 0.0))
            scored.append((pclass, risk_score, route_penalty, demand, oid))

        p1 = sorted([row for row in scored if row[0] == "P1"], key=lambda r: (-r[1], r[2], r[4]))
        p2 = sorted([row for row in scored if row[0] == "P2"], key=lambda r: (-r[1], r[2], r[4]))
        p3 = sorted([row for row in scored if row[0] == "P3"], key=lambda r: (-r[1], r[2], r[4]))

        committed_ids: list[str] = []
        buffered_ids: list[str] = []
        deferred_ids: list[str] = []
        load = 0.0
        for _, _, _, demand, oid in p1:
            if load + demand <= float(plan.commitment_capacity_colli):
                committed_ids.append(oid)
                load += demand
            else:
                buffered_ids.append(oid)
        committed_p2: list[str] = []
        for _, _, _, demand, oid in p2:
            if load + demand <= float(plan.commitment_capacity_colli):
                committed_ids.append(oid)
                committed_p2.append(oid)
                load += demand
            else:
                buffered_ids.append(oid)
        buffered_ids.extend(
            [oid for _, _, _, _, oid in p2 if oid not in committed_p2 and oid not in buffered_ids]
        )
        n_release = int(round(len(p3) * float(plan.release_ratio)))
        for idx, (_, _, _, _, oid) in enumerate(p3):
            if idx < n_release:
                buffered_ids.append(oid)
            else:
                deferred_ids.append(oid)

        reserve_ratio = max(
            0.0,
            1.0 - float(plan.commitment_capacity_colli) / max(1.0, float(exec_estimate.effective_capacity_colli)),
        )
        name_map = {
            "conservative": "v6_conservative",
            "balanced": "v6_balanced",
            "recovery_release": "v6_recovery_release",
            "flush": "v6_flush",
        }
        route_intensity_target = (
            "max" if plan.frontier_id == "flush" else "elevated" if plan.frontier_id == "recovery_release" else "normal"
        )
        return ControlAction(
            name=name_map.get(plan.frontier_id, f"v6_{plan.frontier_id}"),
            deadline_guardrail_days=int(plan.guardrail_days),
            urgent_hard_days=int(plan.urgent_hard_days),
            reserve_capacity_ratio=float(reserve_ratio),
            flex_commitment_ratio=1.0,
            p2_criticality_threshold=float(plan.p2_threshold),
            p3_release_ratio=float(plan.release_ratio),
            compute_limit=int(compute_limit),
            risk_budget_epsilon=float(plan.epsilon_today),
            effective_capacity_colli=float(exec_estimate.effective_capacity_colli),
            buffer_capacity_colli=float(plan.buffer_capacity_colli),
            effective_stop_budget=int(exec_estimate.effective_stop_budget),
            fragmentation_risk=float(exec_estimate.fragmentation_risk),
            trip_penalty=float(exec_estimate.trip_penalty),
            route_feasibility_score=float(exec_estimate.route_feasibility_score),
            dispersion_penalty=float(exec_estimate.dispersion_penalty),
            drop_penalty=float(exec_estimate.drop_penalty),
            route_intensity_target=route_intensity_target,
            frontier_id=str(plan.frontier_id),
            committed_order_ids=tuple(committed_ids),
            buffered_order_ids=tuple(buffered_ids),
            deferred_order_ids=tuple(deferred_ids),
        )

    def _materialize_commitment_sets(
        self,
        *,
        action: ControlAction,
        shock_state: ShockState,
        visible_orders: list[dict],
        scenarios,
        buffer_order_ids: set[str],
        carryover_age_map: dict[str, int],
        base_config: dict,
        depot,
    ) -> ControlAction:
        if self.controller_version not in {"v4_event_commitment", "v5_risk_budgeted_commitment", "v6b_value_rerank"}:
            return action

        current_date = datetime.strptime(shock_state.current_date, "%Y-%m-%d")
        p2_threshold = float(action.p2_criticality_threshold or 2.5)
        p3_release_ratio = float(action.p3_release_ratio or 0.0)
        commitment_capacity = shock_state.daily_capacity_colli * (1.0 - float(action.reserve_capacity_ratio or 0.0))
        future_slack = self._expected_future_slack_ratio(shock_state, scenarios)

        scored = []
        for order in visible_orders:
            oid = str(order.get("id"))
            feasible_dates = order.get("feasible_dates") or []
            if shock_state.current_date not in feasible_dates:
                continue
            demand = float(order.get("demand", {}).get("colli", 0.0))
            deadline = feasible_dates[-1] if feasible_dates else None
            if deadline is None:
                continue
            days_left = (datetime.strptime(deadline, "%Y-%m-%d") - current_date).days
            carry_age = float(carryover_age_map.get(oid, 0))
            buffered = 1.0 if oid in buffer_order_ids else 0.0
            if self.controller_version in {"v5_risk_budgeted_commitment", "v6b_value_rerank"}:
                criticality = self._v5_order_risk_score(
                    order=order,
                    days_left=days_left,
                    demand=demand,
                    carry_age=carry_age,
                    buffered=buffered,
                    shock_state=shock_state,
                    scenarios=scenarios,
                    depot=depot,
                    future_slack=future_slack,
                )
            else:
                urgency = 5.0 / (days_left + 1.0)
                size_penalty = 0.20 * (demand / max(1.0, shock_state.daily_capacity_colli))
                scenario_consensus = self._scenario_commitment_score(days_left, shock_state, scenarios)
                criticality = urgency + scenario_consensus + 0.8 * carry_age + 0.5 * buffered - size_penalty
            pclass = "P3"
            if days_left <= int(action.deadline_guardrail_days or 1):
                pclass = "P1"
            elif criticality >= p2_threshold:
                pclass = "P2"
            route_penalty = self._route_burden_penalty(order, depot)
            scored.append((pclass, criticality, route_penalty, demand, oid))

        p1 = sorted([row for row in scored if row[0] == "P1"], key=lambda r: (-r[1], r[2], r[4]))
        p2 = sorted([row for row in scored if row[0] == "P2"], key=lambda r: (-r[1], r[2], r[4]))
        p3 = sorted([row for row in scored if row[0] == "P3"], key=lambda r: (-r[1], r[2], r[4]))

        committed_ids = []
        buffered_ids = []
        deferred_ids = []
        load = 0.0

        for _, _, _, demand, oid in p1:
            committed_ids.append(oid)
            load += demand

        committed_p2 = []
        for _, _, _, demand, oid in p2:
            if load + demand <= commitment_capacity:
                committed_ids.append(oid)
                committed_p2.append(oid)
                load += demand
            else:
                buffered_ids.append(oid)

        remaining_p2 = [oid for _, _, _, _, oid in p2 if oid not in committed_p2 and oid not in buffered_ids]
        buffered_ids.extend(remaining_p2)

        n_release = int(round(len(p3) * p3_release_ratio))
        for idx, (_, _, _, _, oid) in enumerate(p3):
            if idx < n_release:
                buffered_ids.append(oid)
            else:
                deferred_ids.append(oid)

        return replace(
            action,
            committed_order_ids=tuple(committed_ids),
            buffered_order_ids=tuple(buffered_ids),
            deferred_order_ids=tuple(deferred_ids),
        )

    def _scenario_commitment_score(self, days_left: int, shock_state: ShockState, scenarios) -> float:
        score = 0.0
        for scenario in scenarios:
            future_capacity = shock_state.base_capacity_colli * sum(scenario.capacity_ratios[1:])
            future_demand = shock_state.visible_colli * 0.20 * sum(scenario.arrival_multipliers[1:])
            if days_left <= 0:
                score += 2.0
            elif days_left <= 2:
                score += 1.0
            if future_demand > future_capacity:
                score += 0.5
            if min(scenario.capacity_ratios) < shock_state.capacity_ratio_today:
                score += 0.3
        return score / max(1, len(scenarios))

    def _expected_future_slack_ratio(self, shock_state: ShockState, scenarios) -> float:
        slack = 0.0
        for scenario in scenarios:
            future_capacity = shock_state.base_capacity_colli * sum(scenario.capacity_ratios[1:])
            future_demand = shock_state.visible_colli * 0.20 * sum(scenario.arrival_multipliers[1:])
            slack += (future_capacity - future_demand) / max(1.0, shock_state.daily_capacity_colli)
        return slack / max(1, len(scenarios))

    def _adapt_v5_action(self, *, action: ControlAction, shock_state: ShockState, scenarios) -> ControlAction:
        future_slack = self._expected_future_slack_ratio(shock_state, scenarios)
        backlog_tightness = max(0.0, shock_state.backlog_pressure_ratio - 1.0)
        hard_tightness = max(0.0, shock_state.hard_pressure_ratio - 1.0)

        reserve_ratio = float(action.reserve_capacity_ratio or 0.0)
        reserve_ratio += 0.04 * backlog_tightness
        reserve_ratio += 0.03 * hard_tightness
        reserve_ratio += 0.15 * shock_state.prev_drop_rate
        reserve_ratio -= 0.04 * max(0.0, future_slack)
        reserve_ratio = min(0.24, max(0.02, reserve_ratio))

        flex_ratio = float(action.flex_commitment_ratio or 1.0)
        flex_ratio -= 0.10 * backlog_tightness
        flex_ratio -= 0.08 * shock_state.prev_drop_rate
        flex_ratio += 0.06 * max(0.0, future_slack)
        flex_ratio = min(1.0, max(0.35, flex_ratio))

        p2_threshold = float(action.p2_criticality_threshold or 2.5)
        p2_threshold += 0.8 * max(0.0, -future_slack)
        p2_threshold += 0.5 * shock_state.prev_drop_rate

        p3_release_ratio = float(action.p3_release_ratio or 0.0)
        p3_release_ratio += 0.22 * max(0.0, future_slack)
        p3_release_ratio -= 0.18 * backlog_tightness
        p3_release_ratio -= 0.10 * hard_tightness
        p3_release_ratio = min(1.0, max(0.0, p3_release_ratio))

        compute_limit = int(action.compute_limit or int(self.config.get("base_compute", 60)))
        if shock_state.capacity_ratio_today < 0.70 or shock_state.prev_drop_rate >= 0.10 or future_slack <= -0.30:
            compute_limit = max(compute_limit, 300)
        elif shock_state.capacity_ratio_today < 0.85 or future_slack <= -0.10 or backlog_tightness >= 0.30:
            compute_limit = max(compute_limit, 180)

        carryover_bonus = float(action.carryover_bonus or self.config.get("online_carryover_bonus", 3.0))
        carryover_bonus += 1.5 * backlog_tightness

        return replace(
            action,
            reserve_capacity_ratio=reserve_ratio,
            flex_commitment_ratio=flex_ratio,
            p2_criticality_threshold=p2_threshold,
            p3_release_ratio=p3_release_ratio,
            compute_limit=compute_limit,
            carryover_bonus=carryover_bonus,
        )

    def _route_burden_penalty(self, order: dict, depot) -> float:
        if not isinstance(depot, dict):
            return 0.0
        depot_loc = depot.get("location")
        order_loc = order.get("location")
        if not isinstance(order_loc, (list, tuple)) or len(order_loc) < 2:
            return 0.0
        if not isinstance(depot_loc, (list, tuple)) or len(depot_loc) < 2:
            return 0.0
        ox, oy = float(order_loc[0]), float(order_loc[1])
        dx, dy = float(depot_loc[0]), float(depot_loc[1])
        return ((ox - dx) ** 2 + (oy - dy) ** 2) ** 0.5

    def _v5_order_risk_score(
        self,
        *,
        order: dict,
        days_left: int,
        demand: float,
        carry_age: float,
        buffered: float,
        shock_state: ShockState,
        scenarios,
        depot,
        future_slack: float,
    ) -> float:
        urgency = 6.0 / (days_left + 1.0)
        scenario_consensus = self._scenario_commitment_score(days_left, shock_state, scenarios)
        route_penalty = self._route_burden_penalty(order, depot)
        size_factor = demand / max(1.0, shock_state.daily_capacity_colli)
        slack_risk = max(0.0, -future_slack)
        return (
            urgency
            + 1.25 * scenario_consensus
            + 0.90 * carry_age
            + 0.60 * buffered
            + 1.20 * slack_risk
            + 0.30 * size_factor
            - 0.08 * route_penalty
        )
