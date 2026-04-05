from __future__ import annotations

import csv
import json
import math
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    from src.results_layout import endpoint_name_from_result_file
except ImportError:
    from results_layout import endpoint_name_from_result_file

try:
    from sklearn.ensemble import GradientBoostingRegressor
except Exception:
    GradientBoostingRegressor = None


DEFAULT_V6_VALUE_FEATURES = (
    "capacity_ratio",
    "capacity",
    "visible_open_orders",
    "visible_due_today_count",
    "visible_due_soon_count",
    "planned_today",
    "delivered_today",
    "vrp_dropped",
    "compute_limit_seconds",
    "robust_scenario_loss_mean",
    "robust_scenario_loss_cvar",
    "exec_effective_capacity_colli",
    "exec_effective_capacity_ratio",
    "exec_effective_stop_budget",
    "exec_route_feasibility_score",
    "exec_fragmentation_risk",
    "exec_trip_penalty",
    "exec_route_dispersion_index",
    "v6_risk_budget_epsilon",
    "v6_commitment_capacity_colli",
    "v6_buffer_capacity_colli",
    "v6_commit_count",
    "v6_buffer_count",
    "v6_defer_count",
    "v6_p2_threshold",
    "v6_release_ratio",
    "v6_pred_failure_mean",
    "v6_pred_failure_cvar",
    "v6_pred_penalized_cost_proxy",
    "v6_selected_colli",
    "v6_selected_due_today_colli",
    "v6_selected_due_soon_colli",
    "value_action_reserve_ratio",
    "value_action_flex_ratio",
    "value_action_release_ratio",
    "value_action_compute_limit",
    "value_action_effective_capacity_ratio",
    "value_action_fragmentation_risk",
    "value_action_trip_penalty",
    "value_action_route_feasibility_score",
    "value_action_commit_count",
    "value_action_buffer_count",
    "value_action_defer_count",
)

DEFAULT_V6B2_TRAIN_ENDPOINTS = {
    "scenario1_robust_v5_risk_budgeted",
    "scenario1_robust_v5_risk_budgeted_compute300",
    "scenario1_robust_v5_risk_budgeted_mt3",
    "scenario1_robust_v6b_value_rerank",
    "scenario1_robust_v6b_value_rerank_compute300",
    "scenario1_robust_v6b_value_rerank_mt3_stress",
    "scenario1_robust_v6b1_value_rerank",
    "scenario1_robust_v6b1_value_rerank_compute300",
    "scenario1_robust_v6b1_value_rerank_mt3_stress",
    "scenario1_robust_v6b2_guarded_value_rerank",
    "scenario1_robust_v6b2_guarded_value_rerank_compute300",
    "scenario1_robust_v6b2_guarded_value_rerank_mt3_stress",
}


def _safe_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0.0
        if stripped.lower() in {"nan", "none", "inf", "-inf"}:
            return 0.0
    try:
        out = float(value)
    except Exception:
        return 0.0
    if not math.isfinite(out):
        return 0.0
    return out


def _safe_int(value) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def _safe_target_load(value) -> float:
    out = _safe_float(value)
    return out if out > 0.0 else 0.0


@dataclass(frozen=True)
class LinearValueModelArtifact:
    feature_names: tuple[str, ...]
    feature_means: tuple[float, ...]
    feature_scales: tuple[float, ...]
    weights: tuple[float, ...]
    bias: float
    target_name: str = "target_value_to_go"
    model_kind: str = "linear_standardized"

    def predict(self, features: dict[str, float]) -> float:
        values = np.array([_safe_float(features.get(name, 0.0)) for name in self.feature_names], dtype=float)
        means = np.array(self.feature_means, dtype=float)
        scales = np.array(self.feature_scales, dtype=float)
        standardized = (values - means) / np.where(scales == 0.0, 1.0, scales)
        return float(np.dot(standardized, np.array(self.weights, dtype=float)) + float(self.bias))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "model_kind": self.model_kind,
            "target_name": self.target_name,
            "feature_names": list(self.feature_names),
            "feature_means": list(self.feature_means),
            "feature_scales": list(self.feature_scales),
            "weights": list(self.weights),
            "bias": float(self.bias),
        }

    @classmethod
    def from_json_dict(cls, payload: dict[str, object]) -> "LinearValueModelArtifact":
        return cls(
            feature_names=tuple(str(x) for x in payload.get("feature_names", [])),
            feature_means=tuple(float(x) for x in payload.get("feature_means", [])),
            feature_scales=tuple(float(x) for x in payload.get("feature_scales", [])),
            weights=tuple(float(x) for x in payload.get("weights", [])),
            bias=float(payload.get("bias", 0.0)),
            target_name=str(payload.get("target_name", "target_value_to_go")),
            model_kind=str(payload.get("model_kind", "linear_standardized")),
        )


class V6ValueFeatureBuilder:
    def __init__(self, feature_names: Iterable[str] | None = None):
        self.feature_names = tuple(feature_names or DEFAULT_V6_VALUE_FEATURES)

    def build_from_daily_stat(self, daily_stat: dict) -> dict[str, float]:
        return {name: _safe_float(daily_stat.get(name, 0.0)) for name in self.feature_names}


class V6ValueModel:
    def __init__(self, model_path: str | Path | None = None, fallback_value: float = 0.0):
        self.model_path = Path(model_path) if model_path else None
        self.fallback_value = float(fallback_value)
        self.model = None
        self.feature_names: tuple[str, ...] = tuple()
        self.model_kind = "fallback"
        if self.model_path is not None:
            self._load()

    def _load(self) -> None:
        assert self.model_path is not None
        suffix = self.model_path.suffix.lower()
        if suffix == ".json":
            payload = json.loads(self.model_path.read_text())
            model_kind = str(payload.get("model_kind", "linear_standardized"))
            if model_kind == "linear_standardized":
                self.model = LinearValueModelArtifact.from_json_dict(payload)
                self.feature_names = tuple(self.model.feature_names)
                self.model_kind = model_kind
                return
            if model_kind == "pickle_ref":
                pickle_path = self.model_path.parent / str(payload["pickle_path"])
                with pickle_path.open("rb") as f:
                    pickled = pickle.load(f)
                self.model = pickled["estimator"]
                self.feature_names = tuple(str(x) for x in pickled["feature_names"])
                self.model_kind = model_kind
                return
        with self.model_path.open("rb") as f:
            pickled = pickle.load(f)
        if isinstance(pickled, dict) and "estimator" in pickled and "feature_names" in pickled:
            self.model = pickled["estimator"]
            self.feature_names = tuple(str(x) for x in pickled["feature_names"])
            self.model_kind = str(pickled.get("model_kind", "pickle_estimator"))
            return
        self.model = pickled
        self.feature_names = tuple(getattr(self.model, "feature_names_in_", tuple()))
        self.model_kind = "pickle_estimator"

    def predict(self, features: dict[str, float]) -> float:
        if self.model is None:
            return float(self.fallback_value)
        if isinstance(self.model, LinearValueModelArtifact):
            return self.model.predict(features)
        if hasattr(self.model, "predict"):
            feature_names = self.feature_names or tuple(sorted(features.keys()))
            values = np.array([[_safe_float(features.get(name, 0.0)) for name in feature_names]], dtype=float)
            prediction = self.model.predict(values)
            return float(prediction[0])
        return float(self.fallback_value)


def _build_target_bundle(
    *,
    daily_stats: list[dict],
    idx: int,
    penalty_per_fail: float,
    lambda_deadline: float,
    lambda_gap: float,
) -> dict[str, float]:
    future_daily = daily_stats[idx + 1 :]
    target_failures_to_go = sum(_safe_float(row.get("failures", 0.0)) for row in future_daily)
    target_cost_to_go = sum(_safe_float(row.get("cost", 0.0)) for row in future_daily)
    target_penalized_to_go = float(target_cost_to_go + penalty_per_fail * target_failures_to_go)
    target_deadline_pressure_to_go = sum(
        _safe_float(row.get("visible_due_today_count", 0.0))
        + 0.5 * _safe_float(row.get("visible_due_soon_count", 0.0))
        for row in future_daily
    )
    target_service_gap_to_go = sum(
        max(0.0, _safe_target_load(row.get("target_load", 0.0)) - _safe_float(row.get("served_colli", 0.0)))
        for row in future_daily
    )
    target_value_to_go = float(
        target_penalized_to_go
        + lambda_deadline * target_deadline_pressure_to_go
        + lambda_gap * target_service_gap_to_go
    )
    return {
        "target_failures_to_go": float(target_failures_to_go),
        "target_cost_to_go": float(target_cost_to_go),
        "target_penalized_to_go": float(target_penalized_to_go),
        "target_deadline_pressure_to_go": float(target_deadline_pressure_to_go),
        "target_service_gap_to_go": float(target_service_gap_to_go),
        "target_value_to_go": float(target_value_to_go),
    }


def compute_row_weight(row: dict[str, object]) -> float:
    weight = 1.0
    if _safe_float(row.get("visible_due_today_count", 0.0)) > 0.0:
        weight += 2.0
    if _safe_float(row.get("visible_due_soon_count", 0.0)) > 0.0:
        weight += 1.0
    if _safe_float(row.get("capacity_ratio", 1.0)) < 1.0:
        weight += 1.0
    endpoint = str(row.get("endpoint", ""))
    if "mt3" in endpoint:
        weight *= 1.5
    if "compute300" in endpoint:
        weight *= 1.25
    return min(weight, 5.0)


def filter_value_dataset_rows(
    rows: list[dict[str, object]],
    *,
    filter_policy: str = "none",
) -> list[dict[str, object]]:
    policy = str(filter_policy or "none").lower()
    filtered: list[dict[str, object]] = []
    for row in rows:
        endpoint = str(row.get("endpoint", ""))
        if policy == "v6b2_only" and endpoint not in DEFAULT_V6B2_TRAIN_ENDPOINTS:
            continue
        if str(row.get("robust_action_name", "")) == "":
            continue
        solver_status = str(row.get("solver_status", "success"))
        if solver_status and solver_status != "success":
            continue
        if endpoint not in DEFAULT_V6B2_TRAIN_ENDPOINTS and policy == "v6b2_only":
            continue
        if _safe_float(row.get("visible_open_orders", 0.0)) <= 0.0:
            continue
        filtered.append(row)
    return filtered


def build_value_dataset_rows(
    *,
    simulation_results: dict,
    endpoint: str,
    seed: int,
    feature_names: Iterable[str] | None = None,
    lambda_deadline: float = 40.0,
    lambda_gap: float = 5.0,
) -> list[dict[str, object]]:
    daily_stats = list(simulation_results.get("daily_stats", []))
    if not daily_stats:
        return []
    penalty_per_fail = _safe_float(
        simulation_results.get("penalty_param", simulation_results.get("summary", {}).get("penalty_param", 150.0))
    )
    feature_builder = V6ValueFeatureBuilder(feature_names=feature_names)
    rows: list[dict[str, object]] = []
    for idx, daily_stat in enumerate(daily_stats):
        row = {
            "endpoint": str(endpoint),
            "seed": int(seed),
            "day_index": int(idx),
            "date": str(daily_stat.get("date", "")),
            "penalty_per_fail": float(penalty_per_fail),
            "robust_action_name": str(daily_stat.get("robust_action_name", "")),
            "solver_status": str(daily_stat.get("solver_status", "")),
        }
        row.update(feature_builder.build_from_daily_stat(daily_stat))
        row.update(
            _build_target_bundle(
                daily_stats=daily_stats,
                idx=idx,
                penalty_per_fail=float(penalty_per_fail),
                lambda_deadline=float(lambda_deadline),
                lambda_gap=float(lambda_gap),
            )
        )
        row["row_weight"] = float(compute_row_weight({**daily_stat, **row}))
        rows.append(row)
    return rows


def collect_value_dataset_rows(
    *,
    results_dir: str | Path,
    endpoints: set[str] | None = None,
    feature_names: Iterable[str] | None = None,
    filter_policy: str = "none",
    lambda_deadline: float = 40.0,
    lambda_gap: float = 5.0,
) -> list[dict[str, object]]:
    results_path = Path(results_dir)
    rows: list[dict[str, object]] = []
    for path in sorted(results_path.glob("**/simulation_results.json")):
        if "_analysis" in path.parts:
            continue
        seed_part = path.parent.name
        if not seed_part.startswith("Seed_"):
            continue
        endpoint_part = endpoint_name_from_result_file(path, results_dir=results_path)
        seed = int(seed_part.split("_", 1)[1])
        endpoint = "scenario1_baseline" if endpoint_part == "baseline" else str(endpoint_part)
        if endpoints and endpoint not in endpoints:
            continue
        payload = json.loads(path.read_text())
        rows.extend(
            build_value_dataset_rows(
                simulation_results=payload,
                endpoint=str(endpoint),
                seed=int(seed),
                feature_names=feature_names,
                lambda_deadline=float(lambda_deadline),
                lambda_gap=float(lambda_gap),
            )
        )
    return filter_value_dataset_rows(rows, filter_policy=filter_policy)


def fit_linear_value_model(
    rows: list[dict[str, object]],
    *,
    feature_names: Iterable[str] | None = None,
    target_name: str = "target_value_to_go",
    sample_weight_name: str = "row_weight",
    l2: float = 1e-6,
) -> LinearValueModelArtifact:
    if not rows:
        raise ValueError("Cannot fit v6 value model without rows.")
    features = tuple(feature_names or DEFAULT_V6_VALUE_FEATURES)
    x = np.array([[_safe_float(row.get(name, 0.0)) for name in features] for row in rows], dtype=float)
    y = np.array([_safe_float(row.get(target_name, 0.0)) for row in rows], dtype=float)
    w = np.array([max(1e-6, _safe_float(row.get(sample_weight_name, 1.0))) for row in rows], dtype=float)
    means = x.mean(axis=0)
    scales = x.std(axis=0)
    scales = np.where(scales == 0.0, 1.0, scales)
    x_std = (x - means) / scales
    design = np.hstack([x_std, np.ones((x_std.shape[0], 1), dtype=float)])
    w_sqrt = np.sqrt(w)[:, None]
    design_w = design * w_sqrt
    y_w = y * np.sqrt(w)
    penalty = l2 * np.eye(design.shape[1], dtype=float)
    penalty[-1, -1] = 0.0
    solution = np.linalg.solve(design_w.T @ design_w + penalty, design_w.T @ y_w)
    weights = solution[:-1]
    bias = solution[-1]
    return LinearValueModelArtifact(
        feature_names=features,
        feature_means=tuple(float(v) for v in means),
        feature_scales=tuple(float(v) for v in scales),
        weights=tuple(float(v) for v in weights),
        bias=float(bias),
        target_name=target_name,
    )


def fit_gbt_value_model(
    rows: list[dict[str, object]],
    *,
    feature_names: Iterable[str] | None = None,
    target_name: str = "target_value_to_go",
    sample_weight_name: str = "row_weight",
) -> dict[str, object]:
    if GradientBoostingRegressor is None:
        raise RuntimeError("sklearn GradientBoostingRegressor is unavailable")
    features = tuple(feature_names or DEFAULT_V6_VALUE_FEATURES)
    x = np.array([[_safe_float(row.get(name, 0.0)) for name in features] for row in rows], dtype=float)
    y = np.array([_safe_float(row.get(target_name, 0.0)) for row in rows], dtype=float)
    w = np.array([max(1e-6, _safe_float(row.get(sample_weight_name, 1.0))) for row in rows], dtype=float)
    estimator = GradientBoostingRegressor(
        random_state=0,
        n_estimators=250,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.9,
    )
    estimator.fit(x, y, sample_weight=w)
    return {
        "estimator": estimator,
        "feature_names": list(features),
        "target_name": target_name,
        "model_kind": "gbt_sklearn",
    }


def evaluate_model_mae(
    model,
    rows: list[dict[str, object]],
    *,
    target_name: str,
) -> float:
    if not rows:
        return 0.0
    errors: list[float] = []
    for row in rows:
        if isinstance(model, LinearValueModelArtifact):
            pred = model.predict(row)
        else:
            features = np.array([[_safe_float(row.get(name, 0.0)) for name in model["feature_names"]]], dtype=float)
            pred = float(model["estimator"].predict(features)[0])
        errors.append(abs(pred - _safe_float(row.get(target_name, 0.0))))
    return float(sum(errors) / len(errors))


def write_rows_to_csv(path: str | Path, rows: list[dict[str, object]]) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Cannot write empty v6 value dataset.")
    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def write_model_artifact(
    *,
    model,
    output_path: str | Path,
    target_name: str,
) -> Path:
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(model, LinearValueModelArtifact):
        out_path.write_text(json.dumps(model.to_json_dict(), indent=2))
        return out_path
    pickle_path = out_path.with_suffix(".pkl")
    with pickle_path.open("wb") as f:
        pickle.dump(model, f)
    payload = {
        "model_kind": "pickle_ref",
        "target_name": target_name,
        "feature_names": list(model["feature_names"]),
        "pickle_path": pickle_path.name,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path
