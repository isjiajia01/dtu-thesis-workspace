#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from statistics import mean

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.results_layout import find_endpoint_dir

from sklearn.tree import DecisionTreeClassifier, export_text

BASE_RESULTS = Path("data/results/EXP_EXP01")
BASE_DATA = Path("data/processed")

DATASETS = {
    "herlev": {
        "benchmark": BASE_DATA / "multiday_benchmark_herlev.json",
        "variants": {
            "control": "scenario1_robust_v6g_deadline_reservation_v6d_fixed300_cap05_control",
            "dyn60": "scenario1_robust_v6g_deadline_reservation_v6d_dynrule_noseed_cap05",
            "dyn90": "scenario1_robust_v6g_deadline_reservation_v6d_dynrule_noseed_cap05_chunk90",
            "dyn60_relax": "scenario1_robust_v6g_deadline_reservation_v6d_dynrule_noseed_cap05_chunk60_relax",
            "dyn90_relax": "scenario1_robust_v6g_deadline_reservation_v6d_dynrule_noseed_cap05_chunk90_relax",
        },
    },
    "aalborg": {
        "benchmark": BASE_DATA / "multiday_benchmark_aalborg.json",
        "variants": {
            "control": "scenario1_ood_aalborg_v6g_v6d_ctrl300_cap05",
            "dyn60": "scenario1_ood_aalborg_v6g_v6d_dyn60_cap05",
            "dyn90": "scenario1_ood_aalborg_v6g_v6d_dyn90_cap05",
            "dyn60_relax": "scenario1_ood_aalborg_v6g_v6d_dyn60_relax_cap05",
            "dyn90_relax": "scenario1_ood_aalborg_v6g_v6d_dyn90_relax_cap05",
        },
    },
    "aabyhoj": {
        "benchmark": BASE_DATA / "multiday_benchmark_aabyhoj.json",
        "variants": {
            "control": "scenario1_ood_aabyhoj_v6g_v6d_ctrl300_cap05",
            "dyn60": "scenario1_ood_aabyhoj_v6g_v6d_dyn60_cap05",
            "dyn90": "scenario1_ood_aabyhoj_v6g_v6d_dyn90_cap05",
            "dyn60_relax": "scenario1_ood_aabyhoj_v6g_v6d_dyn60_relax_cap05",
            "dyn90_relax": "scenario1_ood_aabyhoj_v6g_v6d_dyn90_relax_cap05",
        },
    },
    "odense": {
        "benchmark": BASE_DATA / "multiday_benchmark_odense.json",
        "variants": {
            "control": "scenario1_ood_odense_v6g_v6d_ctrl300_cap05",
            "dyn60": "scenario1_ood_odense_v6g_v6d_dyn60_cap05",
            "dyn90": "scenario1_ood_odense_v6g_v6d_dyn90_cap05",
            "dyn60_relax": "scenario1_ood_odense_v6g_v6d_dyn60_relax_cap05",
            "dyn90_relax": "scenario1_ood_odense_v6g_v6d_dyn90_relax_cap05",
        },
    },
}

QUALITY_SR_DROP_MAX = 0.003
QUALITY_FAIL_INCREASE_MAX = 1.5


def load_benchmark_features(path: Path):
    data = json.loads(path.read_text())
    md = data.get("metadata", {})
    horizon_days = 0
    if md.get("horizon_start") and md.get("horizon_end"):
        from datetime import datetime
        s = datetime.strptime(md["horizon_start"], "%Y-%m-%d")
        e = datetime.strptime(md["horizon_end"], "%Y-%m-%d")
        horizon_days = (e - s).days + 1
    return {
        "order_count": len(data.get("orders", [])),
        "vehicle_count": sum(v.get("count", 0) for v in data.get("vehicles", [])),
        "horizon_days": horizon_days,
    }


def load_variant_metrics(endpoint: str):
    root = find_endpoint_dir(BASE_RESULTS, endpoint)
    rows = []
    total_walls = []
    for i in range(1, 11):
        summary = root / f"Seed_{i}" / "DEFAULT" / "Proactive" / "summary_final.json"
        daily = root / f"Seed_{i}" / "DEFAULT" / "Proactive" / "daily_stats.csv"
        if not summary.exists() or not daily.exists():
            continue
        rows.append(json.loads(summary.read_text()))
        with daily.open() as f:
            daily_rows = list(csv.DictReader(f))
        total_walls.append(sum(float(r.get("vrp_wall_seconds", 0.0) or 0.0) for r in daily_rows))
    if not rows:
        return None
    return {
        "n": len(rows),
        "service_rate": mean(float(r.get("service_rate_within_window", 0.0)) for r in rows),
        "failed_orders": mean(float(r.get("failed_orders", 0.0)) for r in rows),
        "penalized_cost": mean(float(r.get("penalized_cost", 0.0)) for r in rows),
        "cost_raw": mean(float(r.get("cost_raw", 0.0)) for r in rows),
        "total_vrp_wall_seconds": mean(total_walls) if total_walls else 0.0,
    }


def choose_best(metrics_by_variant):
    control = metrics_by_variant.get("control")
    if not control:
        return None
    feasible = []
    for name, metrics in metrics_by_variant.items():
        if name == "control" or metrics is None:
            continue
        sr_drop = control["service_rate"] - metrics["service_rate"]
        fail_increase = metrics["failed_orders"] - control["failed_orders"]
        if sr_drop <= QUALITY_SR_DROP_MAX and fail_increase <= QUALITY_FAIL_INCREASE_MAX:
            feasible.append((metrics["total_vrp_wall_seconds"], metrics["penalized_cost"], name))
    if feasible:
        feasible.sort()
        return feasible[0][2]
    candidates = []
    for name, metrics in metrics_by_variant.items():
        if name == "control" or metrics is None:
            continue
        penalty = metrics["penalized_cost"] + 0.05 * metrics["total_vrp_wall_seconds"]
        candidates.append((penalty, name))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


def main():
    dataset_rows = []
    print("# Aggregated metrics")
    for dataset, spec in DATASETS.items():
        features = load_benchmark_features(spec["benchmark"])
        metrics_by_variant = {name: load_variant_metrics(endpoint) for name, endpoint in spec["variants"].items()}
        print(f"\n## {dataset}")
        print(features)
        for name, metrics in metrics_by_variant.items():
            print(name, metrics)
        best = choose_best(metrics_by_variant)
        print("best_variant", best)
        if best is not None:
            dataset_rows.append((features, best))

    if len(dataset_rows) < 2:
        print("\nNot enough completed datasets to distill a rule yet.")
        return

    X = [[r[0]["order_count"], r[0]["vehicle_count"], r[0]["horizon_days"]] for r in dataset_rows]
    y = [r[1] for r in dataset_rows]
    clf = DecisionTreeClassifier(max_leaf_nodes=3, random_state=0)
    clf.fit(X, y)
    print("\n# Distilled rule")
    print(export_text(clf, feature_names=["order_count", "vehicle_count", "horizon_days"]))


if __name__ == "__main__":
    main()
