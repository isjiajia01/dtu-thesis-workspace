import sys
import unittest
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from src.simulation import control_actions as control_actions_mod
from src.simulation import future_sampler as future_sampler_mod
from src.simulation import policies
from src.simulation import robust_controller as robust_controller_mod
from src.simulation import rolling_horizon_integrated as rolling
from src.simulation import shock_state as shock_state_mod


class RobustControllerTests(unittest.TestCase):
    def setUp(self):
        self.current_date = datetime.strptime("2025-12-01", "%Y-%m-%d")
        self.orders = [
            {
                "id": "A",
                "feasible_dates": ["2025-12-01"],
                "demand": {"colli": 4.0},
                "location": [0.0, 0.0],
            },
            {
                "id": "B",
                "feasible_dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
                "demand": {"colli": 4.0},
                "location": [1.0, 0.0],
            },
            {
                "id": "C",
                "feasible_dates": ["2025-12-01", "2025-12-02", "2025-12-03", "2025-12-04", "2025-12-05"],
                "demand": {"colli": 4.0},
                "location": [2.0, 0.0],
            },
        ]
        self.analyzer = rolling.OnlineCapacityAnalyzer(self.orders, self.current_date, 5.0)

    def test_shock_state_builder_counts(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=0,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=10,
            prev_day_vrp_dropped=2,
            prev_day_failures=1,
        )
        self.assertEqual(3, state.visible_orders_count)
        self.assertEqual(1, state.carryover_count)
        self.assertEqual(1, state.due_today_count)
        self.assertEqual(1, state.due_soon_count)
        self.assertGreater(state.backlog_pressure_ratio, 1.0)

    def test_control_action_changes_proactive_selection(self):
        policy = policies.ProactivePolicy({"lookahead_days": 1, "buffer_ratio": 1.0})
        base_selected = policy.select_orders(
            current_date=self.current_date,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            prev_planned_ids=set(),
            daily_capacity_colli=5.0,
        )
        guard_action = control_actions_mod.ControlAction(
            name="guard",
            deadline_guardrail_days=2,
        )
        guarded_selected = policy.select_orders(
            current_date=self.current_date,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            prev_planned_ids=set(),
            daily_capacity_colli=5.0,
            control_action=guard_action,
        )
        self.assertEqual(["A"], [o["id"] for o in base_selected])
        self.assertIn("B", [o["id"] for o in guarded_selected])

    def test_commitment_control_reserves_capacity_for_future(self):
        policy = policies.ProactivePolicy(
            {
                "lookahead_days": 5,
                "buffer_ratio": 1.05,
                "urgent_hard_days": 1,
                "deadline_guardrail_days": 1,
            }
        )
        no_commitment = policy.select_orders(
            current_date=self.current_date,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            prev_planned_ids=set(),
            daily_capacity_colli=8.0,
        )
        commitment_action = control_actions_mod.ControlAction(
            name="commit",
            reserve_capacity_ratio=0.25,
            flex_commitment_ratio=0.4,
            carryover_bonus=5.0,
        )
        with_commitment = policy.select_orders(
            current_date=self.current_date,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            prev_planned_ids=set(),
            daily_capacity_colli=8.0,
            control_action=commitment_action,
        )
        self.assertGreaterEqual(len(no_commitment), len(with_commitment))
        self.assertIn("A", [o["id"] for o in with_commitment])

    def test_future_sampler_and_controller_return_valid_action(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=1,
        )
        sampler = future_sampler_mod.FutureSampler(horizon_days=3)
        belief = sampler.build_belief(state)
        scenarios = sampler.sample(state, belief)
        self.assertEqual(4, len(scenarios))
        self.assertEqual(0.59, scenarios[0].capacity_ratios[0])

        controller = robust_controller_mod.RobustController({"robust_horizon_days": 3})
        policy = policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60})
        decision = controller.choose_action(
            shock_state=state,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
            policy=policy,
            policy_kwargs={
                "current_date": self.current_date,
                "visible_orders": self.orders,
                "analyzer": self.analyzer,
                "prev_planned_ids": set(),
                "daily_capacity_colli": 5.0,
                "prev_selected_ids": set(),
                "capacity_ratio_today": 0.59,
                "prev_day_planned": 12,
                "prev_day_vrp_dropped": 3,
                "depot": {"location": [0.0, 0.0]},
                "n_vehicles": 1,
            },
        )
        self.assertIn(
            decision.action.name,
            {"baseline", "deadline_focus", "routeable_crisis", "balanced_robust"},
        )

    def test_v2_failure_first_prefers_safer_action(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
        )
        controller = robust_controller_mod.RobustController(
            {"robust_horizon_days": 3, "robust_controller_version": "v2"}
        )
        policy = policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60})
        decision = controller.choose_action(
            shock_state=state,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
            policy=policy,
            policy_kwargs={
                "current_date": self.current_date,
                "visible_orders": self.orders,
                "analyzer": self.analyzer,
                "prev_planned_ids": {"B"},
                "daily_capacity_colli": 5.0,
                "prev_selected_ids": set(),
                "capacity_ratio_today": 0.59,
                "prev_day_planned": 12,
                "prev_day_vrp_dropped": 3,
                "depot": {"location": [0.0, 0.0]},
                "n_vehicles": 1,
            },
        )
        self.assertGreaterEqual(decision.failure_risk_cvar, 0.0)
        self.assertGreaterEqual(decision.failure_risk_mean, 0.0)

    def test_v3_commitment_controller_returns_commitment_actions(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
        )
        controller = robust_controller_mod.RobustController(
            {"robust_horizon_days": 3, "robust_controller_version": "v3_commitment"}
        )
        policy = policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60})
        decision = controller.choose_action(
            shock_state=state,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
            policy=policy,
            policy_kwargs={
                "current_date": self.current_date,
                "visible_orders": self.orders,
                "analyzer": self.analyzer,
                "prev_planned_ids": {"B"},
                "daily_capacity_colli": 5.0,
                "prev_selected_ids": set(),
                "capacity_ratio_today": 0.59,
                "prev_day_planned": 12,
                "prev_day_vrp_dropped": 3,
                "depot": {"location": [0.0, 0.0]},
                "n_vehicles": 1,
            },
        )
        self.assertIn(
            decision.action.name,
            {"commit_baseline", "commit_reserve", "commit_triage", "commit_recovery_push"},
        )

    def test_v4_commitment_materializes_commit_sets(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
        )
        controller = robust_controller_mod.RobustController(
            {"robust_horizon_days": 3, "robust_controller_version": "v4_event_commitment"}
        )
        policy = policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60})
        decision = controller.choose_action(
            shock_state=state,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
            policy=policy,
            policy_kwargs={
                "current_date": self.current_date,
                "visible_orders": self.orders,
                "analyzer": self.analyzer,
                "prev_planned_ids": {"B"},
                "buffer_order_ids": {"C"},
                "carryover_age_map": {"B": 2},
                "daily_capacity_colli": 5.0,
                "prev_selected_ids": set(),
                "capacity_ratio_today": 0.59,
                "prev_day_planned": 12,
                "prev_day_vrp_dropped": 3,
                "depot": {"location": [0.0, 0.0]},
                "n_vehicles": 1,
            },
        )
        self.assertIn(
            decision.action.name,
            {
                "commit_hold",
                "commit_shock_triage",
                "commit_release_buffer",
                "commit_flush_recovery",
            },
        )
        self.assertIsNotNone(decision.action.committed_order_ids)
        self.assertIsNotNone(decision.action.buffered_order_ids)
        self.assertIsNotNone(decision.action.deferred_order_ids)

    def test_v5_risk_budget_controller_adapts_commitment_parameters(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
        )
        controller = robust_controller_mod.RobustController(
            {"robust_horizon_days": 3, "robust_controller_version": "v5_risk_budgeted_commitment"}
        )
        policy = policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60})
        decision = controller.choose_action(
            shock_state=state,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
            policy=policy,
            policy_kwargs={
                "current_date": self.current_date,
                "visible_orders": self.orders,
                "analyzer": self.analyzer,
                "prev_planned_ids": {"B"},
                "buffer_order_ids": {"C"},
                "carryover_age_map": {"B": 2},
                "daily_capacity_colli": 5.0,
                "prev_selected_ids": set(),
                "capacity_ratio_today": 0.59,
                "prev_day_planned": 12,
                "prev_day_vrp_dropped": 3,
                "depot": {"location": [0.0, 0.0]},
                "n_vehicles": 1,
            },
        )
        self.assertIn(
            decision.action.name,
            {"risk_guard", "risk_triage", "risk_rebalance", "risk_flush"},
        )
        self.assertIsNotNone(decision.action.committed_order_ids)
        self.assertIsNotNone(decision.action.buffered_order_ids)
        self.assertIsNotNone(decision.action.deferred_order_ids)
        self.assertGreaterEqual(float(decision.action.reserve_capacity_ratio or 0.0), 0.02)
        self.assertGreaterEqual(int(decision.action.compute_limit or 0), 180)

    def test_v6_execaware_controller_returns_effective_capacity_action(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=60,
            prev_day_routes=1,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {"robust_horizon_days": 3, "robust_controller_version": "v6a_execaware_dr_mpc"}
        )
        policy = policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60})
        decision = controller.choose_action(
            shock_state=state,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
            policy=policy,
            policy_kwargs={
                "current_date": self.current_date,
                "visible_orders": self.orders,
                "analyzer": self.analyzer,
                "prev_planned_ids": {"B"},
                "buffer_order_ids": {"C"},
                "carryover_age_map": {"B": 2},
                "daily_capacity_colli": 5.0,
                "prev_selected_ids": set(),
                "capacity_ratio_today": 0.59,
                "prev_day_planned": 12,
                "prev_day_vrp_dropped": 3,
                "depot": {"location": [0.0, 0.0]},
                "n_vehicles": 1,
            },
        )
        self.assertIn(
            decision.action.name,
            {"v6_conservative", "v6_balanced", "v6_recovery_release", "v6_flush"},
        )
        self.assertGreater(float(decision.action.effective_capacity_colli or 0.0), 0.0)
        self.assertGreaterEqual(int(decision.action.effective_stop_budget or 0), 0)
        self.assertIsNotNone(decision.action.frontier_id)
        self.assertIsNotNone(decision.action.committed_order_ids)

    def test_v6a1_execaware_alias_uses_same_path(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=60,
            prev_day_routes=1,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {"robust_horizon_days": 3, "robust_controller_version": "v6a1_execaware_dr_mpc"}
        )
        decision = controller.choose_action(
            shock_state=state,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
            policy=policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60}),
            policy_kwargs={
                "current_date": self.current_date,
                "visible_orders": self.orders,
                "analyzer": self.analyzer,
                "prev_planned_ids": {"B"},
                "buffer_order_ids": {"C"},
                "carryover_age_map": {"B": 2},
                "daily_capacity_colli": 5.0,
                "prev_selected_ids": set(),
                "capacity_ratio_today": 0.59,
                "prev_day_planned": 12,
                "prev_day_vrp_dropped": 3,
                "depot": {"location": [0.0, 0.0]},
                "n_vehicles": 1,
            },
        )
        self.assertTrue(decision.action.name.startswith("v6_"))

    def test_v6b_value_rerank_returns_v5_backbone_action_with_value(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=60,
            prev_day_routes=1,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6b_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        policy = policies.ProactivePolicy({"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60})
        decision = controller.choose_action(
            shock_state=state,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
            policy=policy,
            policy_kwargs={
                "current_date": self.current_date,
                "visible_orders": self.orders,
                "analyzer": self.analyzer,
                "prev_planned_ids": {"B"},
                "buffer_order_ids": {"C"},
                "carryover_age_map": {"B": 2},
                "daily_capacity_colli": 5.0,
                "prev_selected_ids": set(),
                "capacity_ratio_today": 0.59,
                "prev_day_planned": 12,
                "prev_day_vrp_dropped": 3,
                "depot": {"location": [0.0, 0.0]},
                "n_vehicles": 1,
            },
        )
        self.assertIn(
            decision.action.name,
            {"risk_guard", "risk_triage", "risk_rebalance", "risk_flush"},
        )
        self.assertIn(str(decision.action.value_model_kind), {"fallback", "linear_standardized", "pickle_estimator"})

    def test_v6b1_value_rerank_expands_candidate_profiles(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=60,
            prev_day_routes=1,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6b1_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        candidates = controller._build_v6b1_candidate_actions(
            shock_state=state,
            scenarios=controller.future_sampler.sample(state, controller.future_sampler.build_belief(state)),
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
        )
        names = {action.name for action in candidates}
        self.assertGreaterEqual(len(candidates), 6)
        self.assertTrue(any(name.endswith("exec_protect") for name in names))
        self.assertTrue(any(name.endswith("compute_push") for name in names))

    def test_v6b2_guarded_rerank_downgrades_push_under_stress(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=4,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=3,
            vehicle_count_today=1,
            prev_day_compute_limit=60,
            prev_day_routes=1,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6b2_guarded_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        candidates = controller._build_v6b2_candidate_actions(
            shock_state=state,
            scenarios=controller.future_sampler.sample(state, controller.future_sampler.build_belief(state)),
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
        )
        names = {action.name for action in candidates}
        self.assertTrue(any(name.endswith("_guarded") for name in names))
        self.assertTrue(any(str(action.candidate_profile) == "guarded" for action in candidates))

    def test_v6b3_diversified_rerank_adds_cleaner_profiles(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=60,
            prev_day_routes=1,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6b3_diversified_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        candidates = controller._build_v6b3_candidate_actions(
            shock_state=state,
            scenarios=controller.future_sampler.sample(state, controller.future_sampler.build_belief(state)),
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
        )
        profiles = {str(action.candidate_profile) for action in candidates}
        self.assertIn("balanced_release", profiles)
        self.assertIn("carryover_focus", profiles)
        self.assertIn("route_safe", profiles)
        self.assertIn("release_cap", profiles)

    def test_v6e_phase_guarded_adds_onset_profiles(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=0,
            prev_day_failures=0,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=60,
            prev_day_routes=1,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6e_phase_guarded_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        candidates = controller._build_v6e_candidate_actions(
            shock_state=state,
            scenarios=controller.future_sampler.sample(state, controller.future_sampler.build_belief(state)),
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 60},
        )
        names = {action.name for action in candidates}
        profiles = {str(action.candidate_profile) for action in candidates}
        flags = {str(action.guardrail_flags or "") for action in candidates}
        self.assertTrue(any("_onset_" in name for name in names))
        self.assertIn("onset_buffer", profiles)
        self.assertTrue(any("onset_release_cap" in flag or "onset_aggressive" in flag for flag in flags))

    def test_v6e_recovery_release_switches_late_shock_to_recovery(self):
        builder = shock_state_mod.ShockStateBuilder()
        recovery_orders = [
            {
                "id": "A",
                "feasible_dates": ["2025-12-01"],
                "demand": {"colli": 4.0},
                "location": [0.0, 0.0],
            },
            {
                "id": "B",
                "feasible_dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
                "demand": {"colli": 4.0},
                "location": [0.10, 0.0],
            },
            {
                "id": "C",
                "feasible_dates": ["2025-12-01", "2025-12-02", "2025-12-03", "2025-12-04", "2025-12-05"],
                "demand": {"colli": 4.0},
                "location": [0.20, 0.0],
            },
        ]
        state = builder.build(
            day_index=7,
            current_date=self.current_date,
            visible_orders=recovery_orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=20.0,
            capacity_ratio_today=0.59,
            prev_day_planned=20,
            prev_day_vrp_dropped=2,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=300,
            prev_day_routes=2,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6e_recovery_release_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        scenarios = controller.future_sampler.sample(state, controller.future_sampler.build_belief(state))
        phase = controller._infer_v6e_phase(state, scenarios)
        candidates = controller._build_v6e_candidate_actions(
            shock_state=state,
            scenarios=scenarios,
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 300},
        )
        names = {action.name for action in candidates}
        flags = {str(action.guardrail_flags or "") for action in candidates}
        self.assertEqual("recovery", phase)
        self.assertTrue(any("recovery_release_fix" in name for name in names))
        self.assertTrue(any("recovery_release_floor_fix" in flag or "recovery_reserve_cap_fix" in flag or "recovery_flex_restore" in flag for flag in flags))

    def test_v6f_execution_guard_adds_policy_overrides(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=300,
            prev_day_routes=2,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6f_execution_guard_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        candidates = controller._build_v6f_candidate_actions(
            shock_state=state,
            scenarios=controller.future_sampler.sample(state, controller.future_sampler.build_belief(state)),
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 300},
        )
        self.assertTrue(all(getattr(action, "execution_guard_level", 0.0) > 0.0 for action in candidates))
        self.assertTrue(all(getattr(action, "execution_hard_sort_enabled", False) for action in candidates))

    def test_v6g_deadline_reservation_adds_reservation_overrides(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=300,
            prev_day_routes=2,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6g_deadline_reservation_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        candidates = controller._build_v6g_candidate_actions(
            shock_state=state,
            scenarios=controller.future_sampler.sample(state, controller.future_sampler.build_belief(state)),
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 300},
        )
        self.assertTrue(all(getattr(action, "hard_stop_reservation_enabled", False) for action in candidates))
        self.assertTrue(all(getattr(action, "hard_stop_reservation_ratio", 0.0) > 0.0 for action in candidates))
        self.assertTrue(all(getattr(action, "hard_capacity_reservation_ratio", 0.0) > 0.0 for action in candidates))

    def test_v6h_deadline_boost_adds_solver_penalty_multiplier(self):
        builder = shock_state_mod.ShockStateBuilder()
        state = builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=5.0,
            capacity_ratio_today=0.59,
            prev_day_planned=12,
            prev_day_vrp_dropped=3,
            prev_day_failures=2,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=2,
            vehicle_count_today=1,
            prev_day_compute_limit=300,
            prev_day_routes=2,
            depot={"location": [0.0, 0.0]},
        )
        controller = robust_controller_mod.RobustController(
            {
                "robust_horizon_days": 3,
                "robust_controller_version": "v6h_deadline_boost_value_rerank",
                "v6_value_model_path": "missing_model_for_test.json",
            }
        )
        candidates = controller._build_v6h_candidate_actions(
            shock_state=state,
            scenarios=controller.future_sampler.sample(state, controller.future_sampler.build_belief(state)),
            base_config={"lookahead_days": 3, "buffer_ratio": 1.05, "base_compute": 300},
        )
        self.assertTrue(all(getattr(action, "solver_reserved_hard_penalty_multiplier", 1.0) > 1.0 for action in candidates))



if __name__ == "__main__":
    unittest.main()
