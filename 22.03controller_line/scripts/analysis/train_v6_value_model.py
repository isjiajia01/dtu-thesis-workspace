#!/usr/bin/env python3
"""
Train a minimal linear V6 value-to-go model from the exported CSV dataset.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_CODE_DIR = _REPO_ROOT / "code"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

from simulation.v6_value_model import (
    DEFAULT_V6_VALUE_FEATURES,
    evaluate_model_mae,
    fit_gbt_value_model,
    fit_linear_value_model,
    write_model_artifact,
)


DEFAULT_DATASET_PATH = Path("data/results/EXP_EXP01/_analysis_v6_value/v6_value_dataset.csv")
DEFAULT_OUTPUT_PATH = Path("data/results/EXP_EXP01/_analysis_v6_value/v6_value_model.json")


def _safe_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a minimal V6 value model")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--target", default="target_value_to_go")
    parser.add_argument("--valid-seeds", nargs="*", default=None)
    parser.add_argument("--l2", type=float, default=1e-6)
    parser.add_argument("--model-kind", choices=("linear", "gbt", "auto"), default="auto")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        return 1

    with dataset_path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print(f"Dataset is empty: {dataset_path}")
        return 1

    valid_seeds = set(int(seed) for seed in args.valid_seeds) if args.valid_seeds else set()
    train_rows = [row for row in rows if int(row["seed"]) not in valid_seeds] or rows
    valid_rows = [row for row in rows if int(row["seed"]) in valid_seeds]

    candidates = {}
    candidates["linear"] = fit_linear_value_model(
        train_rows,
        feature_names=DEFAULT_V6_VALUE_FEATURES,
        target_name=args.target,
        l2=float(args.l2),
    )
    if args.model_kind in {"gbt", "auto"}:
        try:
            candidates["gbt"] = fit_gbt_value_model(
                train_rows,
                feature_names=DEFAULT_V6_VALUE_FEATURES,
                target_name=args.target,
            )
        except Exception:
            if args.model_kind == "gbt":
                raise

    if args.model_kind == "linear":
        chosen_kind = "linear"
    elif args.model_kind == "gbt":
        chosen_kind = "gbt"
    else:
        scores = {kind: evaluate_model_mae(model, valid_rows or train_rows, target_name=args.target) for kind, model in candidates.items()}
        chosen_kind = min(scores, key=scores.get)
        if "linear" in scores and "gbt" in scores:
            if abs(scores["linear"] - scores["gbt"]) / max(1.0, min(scores["linear"], scores["gbt"])) <= 0.02:
                chosen_kind = "linear"
        for kind, score in scores.items():
            print(f"{kind}_mae={score:.6f}")
    artifact = candidates[chosen_kind]

    output_path = Path(args.output)
    write_model_artifact(model=artifact, output_path=output_path, target_name=args.target)

    if valid_rows:
        mae = evaluate_model_mae(artifact, valid_rows, target_name=args.target)
        print(f"valid_mae={mae:.6f}")
    print(f"model_kind={chosen_kind}")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
