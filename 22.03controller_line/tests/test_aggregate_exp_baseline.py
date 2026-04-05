import importlib.util
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


def _load_module(name: str, rel_path: str):
    module_path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


aggregate_exp_baseline = _load_module(
    "aggregate_exp_baseline",
    "scripts/analysis/aggregate_exp_baseline.py",
)


class AggregateExpBaselineTests(unittest.TestCase):
    def test_collect_and_aggregate_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for seed, service_rate, failed_orders in [(1, 0.90, 10), (2, 1.00, 0)]:
                target = root / "baseline" / f"Seed_{seed}"
                target.mkdir(parents=True, exist_ok=True)
                (target / "summary_final.json").write_text(
                    json.dumps(
                        {
                            "strategy": "Greedy",
                            "service_rate": service_rate,
                            "failed_orders": failed_orders,
                            "cost_raw": 100.0 + seed,
                            "penalized_cost": 200.0 + seed,
                            "cost_per_order": 5.0,
                            "plan_churn": 0.2,
                            "load_mse": 10.0,
                        }
                    )
                )

            rows = aggregate_exp_baseline.collect_rows(root)
            self.assertEqual(2, len(rows))
            aggregates = aggregate_exp_baseline.aggregate_rows(rows)
            metrics = {row["metric"]: row for row in aggregates}
            self.assertAlmostEqual(0.95, metrics["service_rate"]["mean"])
            self.assertAlmostEqual(5.0, metrics["failed_orders"]["mean"])


if __name__ == "__main__":
    unittest.main()
