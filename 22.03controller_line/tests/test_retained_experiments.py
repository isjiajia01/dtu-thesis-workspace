import importlib.util
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


experiment_definitions = _load_module("experiment_definitions", "scripts/experiment_definitions.py")
generate_hpc_jobs = _load_module("generate_hpc_jobs", "scripts/runner/generate_hpc_jobs.py")


class RetainedExperimentTests(unittest.TestCase):
    def test_only_retained_experiments_remain(self):
        self.assertEqual({"EXP00", "EXP-BASELINE", "EXP01"}, set(experiment_definitions.EXPERIMENTS.keys()))

    def test_hpc_generation_writes_no_risk_model_checks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_hpc_jobs.generate_job_script(
                "EXP01",
                experiment_definitions.EXPERIMENTS["EXP01"],
                output_dir=tmpdir,
                mode="proactive",
            )
            text = Path(output_path).read_text()
            self.assertIn('scripts.runner.master_runner --exp EXP01', text)
            self.assertNotIn("risk_model.joblib", text)
            self.assertNotIn("use_risk_model", text)

    def test_exp_baseline_defaults_to_greedy_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = generate_hpc_jobs.generate_job_script(
                "EXP-BASELINE",
                experiment_definitions.EXPERIMENTS["EXP-BASELINE"],
                output_dir=tmpdir,
                mode="proactive",
            )
            text = Path(output_path).read_text()
            self.assertIn("# Business-as-usual greedy baseline on the retained HPC pipeline. (greedy)", text)
            self.assertIn('scripts.runner.master_runner --exp EXP-BASELINE', text)
            self.assertNotIn('--override "mode=greedy"', text)


if __name__ == "__main__":
    unittest.main()
