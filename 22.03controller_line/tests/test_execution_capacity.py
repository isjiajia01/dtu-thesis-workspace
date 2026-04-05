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
from src.simulation import execution_capacity as execution_capacity_mod
from src.simulation import future_sampler as future_sampler_mod
from src.simulation import policies
from src.simulation import rolling_horizon_integrated as rolling
from src.simulation import shock_state as shock_state_mod
from src.simulation import v6_risk_budget as v6_risk_budget_mod


class ExecutionCapacityTests(unittest.TestCase):
    def setUp(self):
        self.current_date = datetime.strptime("2025-12-01", "%Y-%m-%d")
        self.orders = [
            {
                "id": "A",
                "feasible_dates": ["2025-12-01"],
                "demand": {"colli": 3.0},
                "location": [0.0, 0.0],
            },
            {
                "id": "B",
                "feasible_dates": ["2025-12-01", "2025-12-02"],
                "demand": {"colli": 3.0},
                "location": [1.0, 0.0],
            },
            {
                "id": "C",
                "feasible_dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
                "demand": {"colli": 3.0},
                "location": [3.0, 0.0],
            },
        ]
        self.analyzer = rolling.OnlineCapacityAnalyzer(self.orders, self.current_date, 8.0)

    def _build_state(self, *, max_trips: int, prev_drop_rate_planned: int = 10, prev_drop_rate_dropped: int = 2):
        builder = shock_state_mod.ShockStateBuilder()
        return builder.build(
            day_index=5,
            current_date=self.current_date,
            visible_orders=self.orders,
            prev_planned_ids={"B"},
            daily_capacity_colli=8.0,
            capacity_ratio_today=0.59,
            prev_day_planned=prev_drop_rate_planned,
            prev_day_vrp_dropped=prev_drop_rate_dropped,
            prev_day_failures=1,
            buffer_order_ids={"C"},
            max_trips_per_vehicle=max_trips,
            vehicle_count_today=2,
            prev_day_compute_limit=60,
            prev_day_routes=2,
            depot={"location": [0.0, 0.0]},
        )

    def test_execution_capacity_penalizes_mt3(self):
        estimator = execution_capacity_mod.ExecutionCapacityEstimator()
        mt2 = estimator.estimate(shock_state=self._build_state(max_trips=2), compute_limit=60)
        mt3 = estimator.estimate(shock_state=self._build_state(max_trips=3), compute_limit=60)
        self.assertLess(mt3.effective_capacity_colli, mt2.effective_capacity_colli)
        self.assertLess(mt3.trip_penalty, mt2.trip_penalty)

    def test_execution_capacity_rewards_compute300(self):
        estimator = execution_capacity_mod.ExecutionCapacityEstimator()
        low = estimator.estimate(shock_state=self._build_state(max_trips=2), compute_limit=60)
        high = estimator.estimate(shock_state=self._build_state(max_trips=2), compute_limit=300)
        self.assertGreater(high.effective_capacity_colli, low.effective_capacity_colli)
        self.assertGreater(high.route_feasibility_score, low.route_feasibility_score)

    def test_v6_frontier_is_monotone(self):
        state = self._build_state(max_trips=2)
        estimator = execution_capacity_mod.ExecutionCapacityEstimator()
        exec_est = estimator.estimate(shock_state=state, compute_limit=60)
        sampler = future_sampler_mod.FutureSampler(horizon_days=3)
        scenarios = sampler.sample(state, sampler.build_belief(state))
        budgeter = v6_risk_budget_mod.ScenarioRiskBudgeter()
        frontier = {plan.frontier_id: plan for plan in budgeter.build_frontier(shock_state=state, scenarios=scenarios, exec_estimate=exec_est)}
        self.assertLessEqual(frontier["conservative"].commitment_capacity_colli, frontier["balanced"].commitment_capacity_colli)
        self.assertLessEqual(frontier["balanced"].commitment_capacity_colli, frontier["recovery_release"].commitment_capacity_colli)

    def test_policy_uses_effective_capacity_not_physical_capacity(self):
        policy = policies.ProactivePolicy({"lookahead_days": 5, "buffer_ratio": 1.05})
        action = control_actions_mod.ControlAction(
            name="v6_balanced",
            effective_capacity_colli=3.5,
            effective_stop_budget=1,
        )
        selected = policy.select_orders(
            current_date=self.current_date,
            visible_orders=self.orders,
            analyzer=self.analyzer,
            prev_planned_ids=set(),
            daily_capacity_colli=8.0,
            control_action=action,
        )
        self.assertLessEqual(sum(float(o["demand"]["colli"]) for o in selected), 8.0)
        self.assertLessEqual(len(selected), 2)


if __name__ == "__main__":
    unittest.main()
