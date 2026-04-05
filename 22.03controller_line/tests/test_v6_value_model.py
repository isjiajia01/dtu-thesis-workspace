import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from src.simulation import v6_value_model as v6_value_model_mod


class V6ValueModelTests(unittest.TestCase):
    def test_build_value_dataset_rows_uses_future_to_go_targets(self):
        payload = {
            "penalty_param": 100.0,
            "daily_stats": [
                {"date": "2025-12-01", "cost": 10.0, "failures": 1.0, "capacity_ratio": 0.8, "visible_due_today_count": 1, "visible_due_soon_count": 2, "target_load": 50.0, "served_colli": 40.0, "robust_action_name": "risk_guard"},
                {"date": "2025-12-02", "cost": 20.0, "failures": 2.0, "capacity_ratio": 0.7, "visible_due_today_count": 2, "visible_due_soon_count": 4, "target_load": 45.0, "served_colli": 30.0, "robust_action_name": "risk_guard"},
                {"date": "2025-12-03", "cost": 30.0, "failures": 3.0, "capacity_ratio": 0.6, "visible_due_today_count": 3, "visible_due_soon_count": 6, "target_load": 40.0, "served_colli": 10.0, "robust_action_name": "risk_guard"},
            ],
        }
        rows = v6_value_model_mod.build_value_dataset_rows(
            simulation_results=payload,
            endpoint="scenario1_robust_v6a_execaware",
            seed=1,
        )
        self.assertEqual(3, len(rows))
        self.assertEqual(30.0, rows[1]["target_cost_to_go"])
        self.assertEqual(3.0, rows[1]["target_failures_to_go"])
        self.assertEqual(330.0, rows[1]["target_penalized_to_go"])
        self.assertEqual(6.0, rows[1]["target_deadline_pressure_to_go"])
        self.assertEqual(30.0, rows[1]["target_service_gap_to_go"])
        self.assertEqual(330.0 + 40.0 * 6.0 + 5.0 * 30.0, rows[1]["target_value_to_go"])
        self.assertEqual(0.0, rows[2]["target_penalized_to_go"])

    def test_linear_value_model_round_trip_predicts(self):
        rows = [
            {"capacity_ratio": 1.0, "target_value_to_go": 10.0, "row_weight": 1.0},
            {"capacity_ratio": 2.0, "target_value_to_go": 20.0, "row_weight": 1.0},
            {"capacity_ratio": 3.0, "target_value_to_go": 30.0, "row_weight": 1.0},
        ]
        artifact = v6_value_model_mod.fit_linear_value_model(
            rows,
            feature_names=("capacity_ratio",),
            target_name="target_value_to_go",
        )
        prediction = artifact.predict({"capacity_ratio": 4.0})
        self.assertGreater(prediction, 30.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.json"
            path.write_text(json.dumps(artifact.to_json_dict(), indent=2))
            model = v6_value_model_mod.V6ValueModel(model_path=path)
            loaded_prediction = model.predict({"capacity_ratio": 4.0})
            self.assertAlmostEqual(prediction, loaded_prediction, places=6)

    def test_filter_policy_v6b2_only_excludes_unwanted_endpoints(self):
        rows = [
            {"endpoint": "scenario1_robust_v5_risk_budgeted", "robust_action_name": "risk_guard", "solver_status": "success", "visible_open_orders": 1},
            {"endpoint": "scenario1_robust_v6a_execaware", "robust_action_name": "v6_conservative", "solver_status": "success", "visible_open_orders": 1},
            {"endpoint": "scenario1_robust_v6b2_guarded_value_rerank", "robust_action_name": "risk_flush", "solver_status": "success", "visible_open_orders": 1},
        ]
        filtered = v6_value_model_mod.filter_value_dataset_rows(rows, filter_policy="v6b2_only")
        self.assertEqual(2, len(filtered))
        self.assertTrue(all(row["endpoint"] != "scenario1_robust_v6a_execaware" for row in filtered))

    def test_row_weight_upweights_stress_rows(self):
        base = {
            "endpoint": "scenario1_robust_v5_risk_budgeted",
            "visible_due_today_count": 0,
            "visible_due_soon_count": 0,
            "capacity_ratio": 1.0,
        }
        stress = {
            "endpoint": "scenario1_robust_v5_risk_budgeted_mt3_compute300",
            "visible_due_today_count": 1,
            "visible_due_soon_count": 1,
            "capacity_ratio": 0.59,
        }
        self.assertGreater(v6_value_model_mod.compute_row_weight(stress), v6_value_model_mod.compute_row_weight(base))


if __name__ == "__main__":
    unittest.main()
