import tempfile
import unittest
from pathlib import Path

from src.results_layout import endpoint_name_from_result_file, find_endpoint_dir, iter_endpoint_dirs


class ResultsLayoutTests(unittest.TestCase):
    def test_iter_endpoint_dirs_finds_nested_endpoints_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "_analysis_suite").mkdir()
            (root / "_retained" / "scenario1_robust_v6g_deadline_reservation_v6d_compute300" / "Seed_1").mkdir(parents=True)
            (root / "_historical" / "scenario1_robust_v6b2_guarded_value_rerank_compute300" / "Seed_2").mkdir(parents=True)

            names = [path.name for path in iter_endpoint_dirs(root)]
            self.assertEqual(
                [
                    "scenario1_robust_v6b2_guarded_value_rerank_compute300",
                    "scenario1_robust_v6g_deadline_reservation_v6d_compute300",
                ],
                names,
            )

    def test_find_endpoint_dir_resolves_nested_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "_retained" / "baseline"
            (target / "Seed_1").mkdir(parents=True)
            resolved = find_endpoint_dir(root, "baseline")
            self.assertEqual(target, resolved)

    def test_endpoint_name_from_result_file_uses_seed_ancestor_parent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            summary = root / "_historical" / "scenario1_robust_v6h_deadline_boost_v6d_compute300" / "Seed_3" / "DEFAULT" / "Proactive" / "summary_final.json"
            summary.parent.mkdir(parents=True)
            summary.write_text("{}", encoding="utf-8")
            self.assertEqual(
                "scenario1_robust_v6h_deadline_boost_v6d_compute300",
                endpoint_name_from_result_file(summary, results_dir=root),
            )


if __name__ == "__main__":
    unittest.main()
