#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rolling Horizon Integrated simulator (patched)

Key fixes vs your previous patched version:
1) Output directory structure is compatible with analysis scripts:
   - self.base_dir points to the "run root" (optionally a run_id folder)
   - self.run_dir is ALWAYS: <base_dir>/<scenario>/<strategy>
   This matches scripts expecting: <base_dir>/<scenario>/<strategy>/daily_stats.csv

2) __init__ is robust to experiment script signature drift:
   - accepts **kwargs and provides safe defaults for seed/verbose/run_context/results_dir/run_id/base_dir.

3) Import robustness:
   - ensures the repository root (folder containing "src/") is on sys.path
     so running from src/experiments works without manual PYTHONPATH tweaks.

Behavioral logic retained from your patched version:
- Always generates failed_orders.csv (even if empty).
- Failure logging with reasons:
    * vrp_dropped_on_deadline
    * policy_rejected_or_unserved (post-VRP sweep)
- failed_orders count uses failed_orders_log length (source of truth).
- plan_churn_effective uses carryover-pool Jaccard distance.

This file is intended to replace:
  src/simulation/rolling_horizon_integrated.py
"""

import copy
import json
import os
import signal
import sys
import time
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

ConfigDict = Mapping[str, Any]
JsonDict = dict[str, Any]


def _as_dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_list_of_dicts(value: Any) -> list[JsonDict]:
    return [item for item in _as_list(value) if isinstance(item, dict)]


def _as_result_dict(value: Any) -> Optional[JsonDict]:
    return value if isinstance(value, dict) else None


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _project_prev_day_route_seed(prev_day_route_summaries: Any, todays_orders: list[JsonDict]) -> list[list[str]]:
    prev_routes = _as_list_of_dicts(prev_day_route_summaries)
    if not prev_routes:
        return []
    todays_order_ids = {
        str(order.get("id")) for order in todays_orders if order.get("id") is not None
    }
    if not todays_order_ids:
        return []

    projected_by_vehicle: dict[int, list[str]] = {}
    max_vehicle_id = -1
    sorted_routes = sorted(
        prev_routes,
        key=lambda route: (
            _as_int(route.get("trip_id"), 1),
            _as_int(route.get("vehicle_id"), 10**9),
        ),
    )
    for route in sorted_routes:
        if _as_int(route.get("trip_id"), 1) != 1:
            continue
        vehicle_id = _as_int(route.get("vehicle_id"), -1)
        if vehicle_id < 0 or vehicle_id in projected_by_vehicle:
            continue
        projected_stops = [
            str(stop)
            for stop in _as_list(route.get("stops", []))
            if str(stop) in todays_order_ids
        ]
        if not projected_stops:
            continue
        projected_by_vehicle[vehicle_id] = projected_stops
        max_vehicle_id = max(max_vehicle_id, int(vehicle_id))

    if not projected_by_vehicle:
        return []
    return [list(projected_by_vehicle.get(vehicle_id, [])) for vehicle_id in range(max_vehicle_id + 1)]


def resolve_runtime_mode(
    *,
    visible_open_orders: int,
    due_today_count: int,
    due_soon_count: int,
    mandatory_count: int,
    capacity_ratio_today: float,
    prev_day_vrp_dropped: Optional[int],
    prev_day_failures: int,
    prev_day_warehouse_reason_code: str,
) -> tuple[str, str]:
    reason_code = str(prev_day_warehouse_reason_code or "").strip().lower()
    prev_drop = int(prev_day_vrp_dropped or 0)
    if (
        reason_code == "due_to_picking_throughput_or_staging"
        or visible_open_orders >= 1000
        or mandatory_count >= 250
        or due_today_count >= 200
        or capacity_ratio_today <= 0.70
        or prev_drop >= 40
        or prev_day_failures >= 15
    ):
        return "fixed300", "depot_or_heavy_pressure"

    if (
        visible_open_orders >= 250
        or mandatory_count >= 80
        or due_today_count >= 50
        or due_soon_count >= 100
        or capacity_ratio_today < 0.95
        or prev_drop > 0
        or prev_day_failures > 0
    ):
        return "dyn90", "moderate_pressure"

    return "dyn60", "light_pressure"


def _disable_stdio() -> None:
    try:
        devnull = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        return
    try:
        sys.stdout = devnull
    except Exception:
        pass
    try:
        sys.stderr = devnull
    except Exception:
        pass


def _safe_print(*values, sep: str = " ", end: str = "\n") -> None:
    stream = getattr(sys, "stdout", None) or sys.__stdout__
    if stream is None:
        return
    message = sep.join(str(value) for value in values) + end
    try:
        stream.write(message)
        stream.flush()
    except (BrokenPipeError, OSError, ValueError):
        _disable_stdio()


# ==========================================
# Retained thesis line imports
# ==========================================
_REPO_ROOT = Path(__file__).resolve().parents[2]

from ..solvers.alns_solver import RoutingGlsSolver
from .policies import GreedyPolicy, ProactivePolicy, StabilityPolicy
from .robust_controller import RobustController
from .shock_state import ShockStateBuilder


# ==========================================
# Helper Functions
# ==========================================
def is_order_released(order, current_date):
    r_date_str = order.get("release_date") or order.get("order_date")
    if not r_date_str:
        return True
    r_dt = datetime.strptime(r_date_str, "%Y-%m-%d")
    return r_dt <= current_date


def calculate_real_daily_capacity(vehicles_config, availability_ratio=1.0):
    total_colli = 0
    total_volume = 0
    adjusted_config = []
    for v_type in vehicles_config:
        original_count = v_type["count"]
        active_count = int(original_count * availability_ratio)
        cap = v_type["capacity"]
        total_colli += active_count * cap["colli"]
        total_volume += active_count * cap["volume"]
        v_copy = copy.deepcopy(v_type)
        v_copy["count"] = active_count
        adjusted_config.append(v_copy)
    return total_colli, total_volume, adjusted_config


def _normalize_stop_to_order_id(stop, todays_orders, orders_map):
    """Normalize routing-solver route stops to real order ids."""
    if stop is None:
        return None
    if stop in orders_map:
        return stop
    if stop == 0 or stop == "0" or stop == "DEPOT" or stop == "depot":
        return None
    if isinstance(stop, int):
        idx = stop - 1
        if 0 <= idx < len(todays_orders):
            oid = todays_orders[idx].get("id")
            return oid if oid in orders_map else None
    if isinstance(stop, str) and stop.isdigit():
        idx = int(stop) - 1
        if 0 <= idx < len(todays_orders):
            oid = todays_orders[idx].get("id")
            return oid if oid in orders_map else None
    return None


def _normalize_dropped_to_order_id(d, todays_orders, orders_map):
    """Normalize routing-solver dropped indices or ids to real order ids."""
    if d is None:
        return None
    if d in orders_map:
        return d
    if isinstance(d, (list, tuple)) and len(d) > 0:
        return _normalize_dropped_to_order_id(d[0], todays_orders, orders_map)
    if isinstance(d, int):
        idx = d - 1
        if 0 <= idx < len(todays_orders):
            oid = todays_orders[idx].get("id")
            return oid if oid in orders_map else None
    if isinstance(d, str) and d.isdigit():
        return _normalize_dropped_to_order_id(int(d), todays_orders, orders_map)
    return None


def _days_until(date_str, current_date) -> int:
    if not date_str:
        return 999
    try:
        target_dt = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return 999
    return (target_dt - current_date).days


def _estimate_mandatory_count(visible_orders, reference_date, guard_days: int) -> int:
    mandatory = 0
    for order in visible_orders:
        feasible_dates = order.get("feasible_dates") or []
        if not feasible_dates:
            continue
        deadline = feasible_dates[-1]
        if _days_until(deadline, reference_date) <= guard_days:
            mandatory += 1
    return mandatory


def _information_mode(config: Optional[ConfigDict]) -> str:
    config_map = _as_dict(config)
    return _as_str(config_map.get("information_mode"), "strict_online").lower()


def _uses_forecast_information(config: Optional[dict]) -> bool:
    return _information_mode(config) in {
        "forecast_informed",
        "oracle",
        "full_oracle",
        "legacy_oracle",
    }


# ==========================================
# Global Capacity Analyzer
# ==========================================
class GlobalCapacityAnalyzer:
    def __init__(
        self, orders, vehicles_config, start_date, end_date, capacity_profile=None
    ):
        self.orders = orders
        self.start_date = start_date
        self.end_date = end_date
        self.vehicles_config = vehicles_config
        self.capacity_profile = capacity_profile if capacity_profile else {}
        self.target_load_profile = {}
        self.order_target_day = {}
        self.daily_capacity_limit = {}
        self.uses_oracle_targets = True

        curr = self.start_date
        day_idx = 0
        while curr <= self.end_date:
            d_str = curr.strftime("%Y-%m-%d")
            ratio = float(self.capacity_profile.get(str(day_idx), 1.0))
            cap_colli, _, _ = calculate_real_daily_capacity(self.vehicles_config, ratio)
            self.daily_capacity_limit[d_str] = cap_colli
            self.target_load_profile[d_str] = 0
            curr += timedelta(days=1)
            day_idx += 1

        self._calculate_target_load_profile()

    def _calculate_target_load_profile(self):
        temp_load = {d: 0 for d in self.target_load_profile}
        sorted_orders = sorted(self.orders, key=lambda x: x["feasible_dates"][-1])

        for order in sorted_orders:
            colli = order["demand"]["colli"]
            best_day = None
            min_load_ratio = float("inf")

            for d_str in order["feasible_dates"]:
                if d_str not in temp_load:
                    continue
                limit = self.daily_capacity_limit.get(d_str, 0)
                if limit <= 0:
                    continue
                ratio = temp_load[d_str] / limit
                if ratio < min_load_ratio:
                    min_load_ratio = ratio
                    best_day = d_str

            if best_day:
                temp_load[best_day] += colli
                self.order_target_day[order["id"]] = best_day
            else:
                fallback = order["feasible_dates"][-1]
                if fallback in temp_load:
                    temp_load[fallback] += colli
                    self.order_target_day[order["id"]] = fallback

        self.target_load_profile = temp_load

    def get_target_day(self, order_id):
        return self.order_target_day.get(order_id, None)

    def get_day_target_load(self, date_str):
        return self.target_load_profile.get(date_str, 0)


class OnlineCapacityAnalyzer:
    """Strict-online planner that avoids full-horizon capacity planning."""

    def __init__(self, orders, current_date, daily_capacity_colli):
        self.orders = orders
        self.current_date = current_date
        self.current_date_str = current_date.strftime("%Y-%m-%d")
        self.daily_capacity_colli = (
            float(daily_capacity_colli) if daily_capacity_colli is not None else 0.0
        )
        self.target_load_profile = {
            self.current_date_str: self._estimate_today_target_load(),
        }
        self.order_target_day = {
            order["id"]: self._earliest_visible_service_day(order)
            for order in self.orders
            if order.get("id") is not None
        }
        self.uses_oracle_targets = False

    def _estimate_today_target_load(self):
        visible_today_load = 0.0
        for order in self.orders:
            feasible_dates = order.get("feasible_dates") or []
            if self.current_date_str in feasible_dates:
                visible_today_load += float(order.get("demand", {}).get("colli", 0.0))
        return min(self.daily_capacity_colli, visible_today_load)

    def _earliest_visible_service_day(self, order):
        feasible_dates = order.get("feasible_dates") or []
        for d_str in feasible_dates:
            if d_str >= self.current_date_str:
                return d_str
        return feasible_dates[-1] if feasible_dates else None

    def get_target_day(self, order_id):
        return self.order_target_day.get(order_id, None)

    def get_day_target_load(self, date_str):
        if date_str == self.current_date_str:
            return self.target_load_profile.get(date_str, np.nan)
        return np.nan


# ==========================================
# Rolling Horizon Integrated
# ==========================================
class RollingHorizonIntegrated:
    def __init__(self, data_source, strategy_config=None, validator=None, **kwargs):
        """
        Args:
            data_source: dict or path to json
            strategy_config: dict for policy configuration
            validator: optional external validator
            **kwargs: accepts (non-exhaustive)
                seed: int
                verbose: bool
                run_context: dict with keys {"scenario","strategy"}
                results_dir: str (parent folder that will contain run_id folder)
                run_id: str (run folder name; defaults to timestamp)
                base_dir: str (explicit run root; if provided, takes precedence over results_dir/run_id)
                scenario_name / strategy_name: optional overrides
        """
        import random

        self.seed = int(kwargs.get("seed", 42))
        random.seed(self.seed)
        self.validator = validator
        self.verbose = bool(kwargs.get("verbose", False))

        self.run_context = kwargs.get("run_context") or {}
        self.scenario_name = self.run_context.get("scenario", "UNKNOWN_SCENARIO")
        self.strategy_name = self.run_context.get("strategy", "UNKNOWN_STRATEGY")

        # optional direct overrides
        self.scenario_name = kwargs.get("scenario_name", self.scenario_name)
        self.strategy_name = kwargs.get("strategy_name", self.strategy_name)

        # ------------------------------
        # Output directory structure
        # ------------------------------
        run_id = kwargs.get("run_id")
        base_dir = kwargs.get("base_dir")  # if provided, this is already the "run root"
        results_dir = kwargs.get("results_dir")

        if base_dir:
            run_root = str(base_dir)
            self.run_id = (
                str(run_id) if run_id else os.path.basename(os.path.normpath(run_root))
            )
        else:
            self.run_id = (
                str(run_id) if run_id else datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            results_dir = (
                str(results_dir)
                if results_dir
                else os.path.join(str(_REPO_ROOT), "data", "results", "thesis_runs")
            )
            run_root = os.path.join(results_dir, self.run_id)

        self.base_dir = run_root  # <-- analysis scripts should pass this as --base_dir
        self.run_dir = os.path.join(
            self.base_dir, self.scenario_name, self.strategy_name
        )
        os.makedirs(self.run_dir, exist_ok=True)

        # ------------------------------
        # Load data
        # ------------------------------
        if isinstance(data_source, str):
            with open(data_source, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
        else:
            loaded_data = data_source

        self.data: JsonDict = _as_dict(loaded_data)
        self.all_orders: list[JsonDict] = _as_list_of_dicts(self.data.get("orders", []))
        self.orders_map: dict[Any, JsonDict] = {
            order["id"]: order for order in self.all_orders if "id" in order
        }
        self.depot: JsonDict = _as_dict(self.data.get("depot", {}))
        self.vehicles_config: list[JsonDict] = _as_list_of_dicts(
            self.data.get("vehicles", [])
        )

        metadata = _as_dict(self.data.get("metadata", {}))
        self.start_date = datetime.strptime(
            _as_str(metadata.get("horizon_start")), "%Y-%m-%d"
        )
        self.end_date = datetime.strptime(
            _as_str(metadata.get("horizon_end")), "%Y-%m-%d"
        )
        self.current_date = self.start_date

        # ------------------------------
        # State
        # ------------------------------
        self.completed_order_ids = set()
        self.failed_order_ids = set()  # for filtering "zombies"
        self.failed_orders_log = []  # structured logs -> failed_orders.csv
        self.daily_stats = []
        self.vrp_audit_traces = []
        self.total_horizon_cost = 0.0
        self._last_completed_date = None
        self._termination_signal = None
        self._install_signal_handlers()

        # churn + stickiness
        self.prev_selected_ids = set()  # yesterday planned set (plan turnover)
        self.prev_suggested_day = {}  # for target churn
        self.prev_planned_ids = set()  # carryover pool: planned-but-not-delivered
        self.buffer_order_ids = set()  # deferred-but-buffered orders for next day
        self.carryover_age = {}
        # previous-day VRP outcomes (for crisis stop-capping heuristics)
        self.prev_day_planned = None
        self.prev_day_vrp_dropped = None
        self.prev_day_compute_limit = None
        self.prev_day_routes = None
        self.prev_day_route_summaries = []
        self.prev_day_warehouse_reason_code = ""

        # ------------------------------
        # Config + policy
        # ------------------------------
        default_config = {
            "mode": "proactive_quota",
            "lookahead_days": 3,
            "buffer_ratio": 1.05,
            "weights": {"urgency": 20.0, "profile": 2.0},
            "penalty_per_fail": 150.0,
            "information_mode": "strict_online",
            "use_robust_controller": False,
            "robust_horizon_days": 3,
        }
        if strategy_config:
            default_config.update(strategy_config)
        self.config = default_config

        mode = self.config["mode"]
        if mode == "greedy":
            self.policy = GreedyPolicy(self.config)
        elif mode == "stability":
            self.policy = StabilityPolicy(self.config)
        else:
            self.policy = ProactivePolicy(self.config)
        self.shock_state_builder = ShockStateBuilder()
        self.robust_controller = None
        if bool(self.config.get("use_robust_controller", False)) and mode != "greedy":
            self.robust_controller = RobustController(self.config)

        # ------------------------------
        # Learned allocator support is intentionally disabled in the retained
        # thesis line. Historical allocator hooks are left as no-op fields so
        # downstream code and saved summaries remain structurally compatible.
        # ------------------------------
        self.learned_allocator = None
        self.bandit_allocator = None
        self.prev_day_failures = 0  # Track previous day failures for audit fields
        self.allocator_type = "disabled"

        if self.config.get("use_learned_allocator", False) and self.verbose:
            _safe_print(
                "[Allocator] Learned allocator support is disabled in the retained thesis line"
            )

    # ---------------------------------
    # Helper: get previous day failures
    # ---------------------------------
    def _get_prev_failures(self):
        """Get the number of failures from the previous day."""
        return self.prev_day_failures

    # ---------------------------------
    # churn(target): target-day churn
    # ---------------------------------
    def calculate_suggestion_churn(self, current_analyzer, visible_orders):
        if not getattr(current_analyzer, "uses_oracle_targets", True):
            self.prev_suggested_day = {}
            return {"count": 0, "rate": 0.0, "intersection": 0}

        churn_count = 0
        common = 0
        current_suggestions = {}

        for order in visible_orders:
            oid = order["id"]
            new_target = current_analyzer.get_target_day(oid)
            current_suggestions[oid] = new_target
            if oid in self.prev_suggested_day:
                common += 1
                if self.prev_suggested_day[oid] != new_target:
                    churn_count += 1

        self.prev_suggested_day = current_suggestions
        return {
            "count": churn_count,
            "rate": (churn_count / common if common > 0 else 0.0),
            "intersection": common,
        }

    def _log_failure(self, oid, d_str, reason):
        """Add a failure entry once (idempotent)."""
        if oid in self.failed_order_ids:
            return
        self.failed_order_ids.add(oid)

        o = self.orders_map.get(oid, {})
        f = {
            "id": oid,
            "scenario": self.scenario_name,
            "strategy": self.strategy_name,
            "fail_date": d_str,
            "deadline": (o.get("feasible_dates") or [None])[-1],
            "release_date": o.get("release_date") or o.get("order_date"),
            "reason": str(reason),
        }
        self.failed_orders_log.append(f)

    def _install_signal_handlers(self):
        for signum in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
            if signum is None:
                continue
            try:
                signal.signal(signum, self._handle_termination_signal)
            except (ValueError, OSError, RuntimeError):
                continue

    def _handle_termination_signal(self, signum, _frame):
        if self._termination_signal is not None:
            raise SystemExit(128 + int(signum))
        self._termination_signal = int(signum)
        try:
            signal_name = signal.Signals(signum).name.lower()
        except Exception:
            signal_name = f"signal_{int(signum)}"
        try:
            self._persist_progress(partial_status=f"terminated_{signal_name}")
        finally:
            raise SystemExit(128 + int(signum))

    def _output_dirs(self):
        candidates = [self.run_dir, self.base_dir]
        output_dirs = []
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            normalized = os.path.normpath(str(candidate))
            if normalized in seen:
                continue
            seen.add(normalized)
            os.makedirs(normalized, exist_ok=True)
            output_dirs.append(normalized)
        return output_dirs

    def _failed_orders_frame(self):
        df_fail = pd.DataFrame(self.failed_orders_log)
        if df_fail.empty:
            df_fail = pd.DataFrame(
                columns=[
                    "id",
                    "scenario",
                    "strategy",
                    "fail_date",
                    "deadline",
                    "release_date",
                    "reason",
                ]
            )
        return df_fail

    def _build_summary(self, *, horizon_end, partial_status):
        if not self.daily_stats:
            return {}

        eligible_orders = [
            o for o in self.all_orders if is_order_released(o, horizon_end)
        ]
        eligible_count = len(eligible_orders)

        delivered_count = len(self.completed_order_ids)
        failed_count = len(self.failed_orders_log)

        total_cost = float(self.total_horizon_cost)
        penalty_per_fail = float(self.config.get("penalty_per_fail", 150.0))
        penalized_cost = total_cost + failed_count * penalty_per_fail

        service_rate = (delivered_count / eligible_count) if eligible_count > 0 else 0.0
        cost_per_order = (total_cost / delivered_count) if delivered_count > 0 else 0.0

        load_target_pairs = []
        for stats in self.daily_stats:
            target_load = stats.get("target_load", np.nan)
            if pd.notna(target_load):
                load_target_pairs.append(
                    (float(stats["served_colli"]), float(target_load))
                )
        load_mse = (
            sum((load - target) ** 2 for load, target in load_target_pairs)
            / len(load_target_pairs)
            if load_target_pairs
            else 0.0
        )

        target_churn_values = [
            float(s["target_churn"])
            for s in self.daily_stats
            if pd.notna(s.get("target_churn", np.nan))
        ]
        avg_target_churn = (
            sum(target_churn_values) / len(target_churn_values)
            if target_churn_values
            else 0.0
        )
        avg_plan_churn_effective = sum(
            float(s["plan_churn_effective"]) for s in self.daily_stats
        ) / len(self.daily_stats)
        avg_plan_churn_raw = sum(
            float(s["plan_churn_raw"]) for s in self.daily_stats
        ) / len(self.daily_stats)

        future_pressure_min = None
        pressure_k_star = None
        try:
            df = pd.DataFrame(self.daily_stats)
            if "capacity_pressure" in df.columns and len(df) > 0:
                pressure_series = df["capacity_pressure"].astype(float)
                valid_pressure = pressure_series.dropna()
                if not valid_pressure.empty:
                    idx = int(valid_pressure.idxmin())
                    future_pressure_min = float(df.loc[idx, "capacity_pressure"])
                    if "pressure_k_star" in df.columns:
                        pk = df.loc[idx, "pressure_k_star"]
                        if pk is not None and pk == pk:
                            pressure_k_star = int(pk)
        except Exception:
            future_pressure_min = None
            pressure_k_star = None

        horizon_end_str = horizon_end.strftime("%Y-%m-%d")
        last_completed_date = self._last_completed_date or self.daily_stats[-1].get("date")
        summary = {
            "run_id": self.run_id,
            "scenario": self.scenario_name,
            "strategy": self.strategy_name,
            "base_dir": self.base_dir,
            "run_dir": self.run_dir,
            "eligible_count": int(eligible_count),
            "delivered_within_window_count": int(delivered_count),
            "deadline_failure_count": int(failed_count),
            "service_rate_within_window": float(service_rate),
            "penalized_cost": penalized_cost,
            "cost_raw": total_cost,
            "cost_per_order": cost_per_order,
            "target_churn": avg_target_churn,
            "plan_churn": avg_plan_churn_effective,
            "plan_churn_raw": avg_plan_churn_raw,
            "load_mse": load_mse,
            "failed_orders": int(failed_count),
            "service_rate": service_rate,
            "penalty_param": float(penalty_per_fail),
            "future_pressure_min": future_pressure_min,
            "pressure_k_star": pressure_k_star,
            "metric_definitions": {
                "eligible_count": "Total unique orders released within simulation window (start_date to end_date)",
                "delivered_within_window_count": "Orders successfully delivered within simulation window",
                "deadline_failure_count": "Orders that reached their deadline day without being delivered",
                "service_rate_within_window": "delivered_within_window_count / eligible_count",
                "note": "Orders with deadlines beyond window end are NOT counted as failures",
            },
            "is_partial": partial_status != "completed",
            "partial_status": partial_status,
            "days_completed": int(len(self.daily_stats)),
            "days_total": int((self.end_date - self.start_date).days + 1),
            "last_completed_date": last_completed_date,
            "horizon_end_evaluated": horizon_end_str,
        }
        if self._termination_signal is not None:
            summary["termination_signal"] = int(self._termination_signal)
        return summary

    def _write_progress_marker(self, *, partial_status):
        payload = {
            "run_id": self.run_id,
            "scenario": self.scenario_name,
            "strategy": self.strategy_name,
            "partial_status": partial_status,
            "days_completed": int(len(self.daily_stats)),
            "days_total": int((self.end_date - self.start_date).days + 1),
            "last_completed_date": self._last_completed_date,
            "termination_signal": self._termination_signal,
            "timestamp": datetime.now().isoformat(),
        }
        for output_dir in self._output_dirs():
            with open(os.path.join(output_dir, "run_progress.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

    def _persist_progress(self, *, partial_status):
        self._write_progress_marker(partial_status=partial_status)
        if not self.daily_stats:
            return

        df = pd.DataFrame(self.daily_stats)
        df_fail = self._failed_orders_frame()
        summary_partial = self._build_summary(
            horizon_end=self.current_date, partial_status=partial_status
        )
        latest_day = dict(self.daily_stats[-1])
        latest_trace = dict(self.vrp_audit_traces[-1]) if self.vrp_audit_traces else {}
        day_number = int(len(self.daily_stats))
        day_label = str(latest_day.get("date") or self._last_completed_date or day_number)
        checkpoint_payload = {
            "partial_status": partial_status,
            "summary": summary_partial,
            "latest_day": latest_day,
            "latest_vrp_audit": latest_trace,
        }
        for output_dir in self._output_dirs():
            df.to_csv(os.path.join(output_dir, "daily_stats.csv"), index=False)
            df_fail.to_csv(os.path.join(output_dir, "failed_orders.csv"), index=False)
            with open(
                os.path.join(output_dir, "summary_partial.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(summary_partial, f, indent=2)

            checkpoint_dir = os.path.join(output_dir, "checkpoints")
            os.makedirs(checkpoint_dir, exist_ok=True)
            with open(
                os.path.join(checkpoint_dir, "checkpoint_latest.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(checkpoint_payload, f, indent=2)
            with open(
                os.path.join(
                    checkpoint_dir,
                    f"day_{day_number:02d}_{day_label.replace('-', '')}.json",
                ),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(checkpoint_payload, f, indent=2)

        _safe_print(
            "[Checkpoint] "
            f"status={partial_status} "
            f"day={day_number}/{int((self.end_date - self.start_date).days + 1)} "
            f"date={day_label} "
            f"planned={int(latest_day.get('planned_today', 0))} "
            f"delivered={int(latest_day.get('delivered_today', 0))} "
            f"fails={int(latest_day.get('failures', 0))} "
            f"dropped={int(latest_day.get('vrp_dropped', 0))} "
            f"solver={latest_day.get('solver_status', '')} "
            f"wall_s={float(latest_day.get('vrp_wall_seconds', 0.0)):.1f} "
            f"service={float(summary_partial.get('service_rate_within_window', 0.0)):.4f}"
        )

    # ---------------------------------
    # main loop
    # ---------------------------------
    def run_simulation(self):
        cap_profile = self.data.get("metadata", {}).get("capacity_profile", {})

        vrp_config = {
            "base_penalty": 2000,
            "urgent_penalty": 1e7,
            "beta": 5.0,
            "epsilon": 0.1,
        }
        for key in (
            "warehouse_filter_max_attempts",
            "warehouse_retry_time_limit_seconds",
            "secondary_trip_time_limit_seconds",
            "secondary_trip_warehouse_retry_time_limit_seconds",
            "solver_chunk_seconds",
            "solver_min_chunks",
            "solver_max_no_improve_chunks",
        ):
            if key in self.config and self.config.get(key) is not None:
                vrp_config[key] = int(self.config.get(key))
        for key in (
            "solver_continue_improvement_ratio",
        ):
            if key in self.config and self.config.get(key) is not None:
                vrp_config[key] = float(self.config.get(key))
        for key in (
            "solver_enable_incumbent_continuation",
            "solver_enable_prev_day_route_seed",
        ):
            if key in self.config and self.config.get(key) is not None:
                vrp_config[key] = bool(self.config.get(key))
        for key in (
            "matrix_dir",
            "vrp_matrix_dir",
        ):
            if key in self.config and self.config.get(key):
                vrp_config[key] = str(self.config.get(key))

        while self.current_date <= self.end_date:
            d_str = self.current_date.strftime("%Y-%m-%d")
            day_idx = (self.current_date - self.start_date).days

            # --- visible orders (filter completed + failed zombies) ---
            visible_open_orders = [
                o
                for o in self.all_orders
                if o["id"] not in self.completed_order_ids
                and o["id"] not in self.failed_order_ids
                and is_order_released(o, self.current_date)
            ]

            # capacity
            ratio = float(cap_profile.get(str(day_idx), 1.0))
            daily_cap_colli, _, adjusted_vehicles = calculate_real_daily_capacity(
                self.vehicles_config, ratio
            )

            # number of vehicles today (optional; some policies use it)
            try:
                n_vehicles_today = int(
                    sum(v.get("count", 0) for v in adjusted_vehicles)
                )
            except Exception:
                n_vehicles_today = 0

            forecast_informed = _uses_forecast_information(self.config)

            # pressure window
            lookahead_check = int(self.config.get("pressure_lookahead", 7))
            ratios_window = [
                float(cap_profile.get(str(day_idx + k), 1.0))
                for k in range(0, lookahead_check + 1)
            ]
            min_ratio = min(ratios_window) if ratios_window else float(ratio)
            k_star = ratios_window.index(min_ratio) if ratios_window else None

            if forecast_informed:
                analyzer = GlobalCapacityAnalyzer(
                    visible_open_orders,
                    self.vehicles_config,
                    self.current_date,
                    self.end_date,
                    capacity_profile=cap_profile,
                )
            else:
                analyzer = OnlineCapacityAnalyzer(
                    visible_open_orders,
                    self.current_date,
                    daily_cap_colli,
                )
                min_ratio = float(ratio)
                k_star = None

            # --- policy selection ---
            carry_prev = set(self.prev_planned_ids) if self.prev_planned_ids else set()
            policy_kwargs = {
                "current_date": self.current_date,
                "visible_orders": visible_open_orders,
                "analyzer": analyzer,
                "prev_planned_ids": self.prev_planned_ids,
                "buffer_order_ids": self.buffer_order_ids,
                "carryover_age_map": self.carryover_age,
                "daily_capacity_colli": daily_cap_colli,
                "prev_selected_ids": self.prev_selected_ids,
                "capacity_ratio_today": ratio,
                "prev_day_planned": self.prev_day_planned,
                "prev_day_vrp_dropped": self.prev_day_vrp_dropped,
                "depot": self.depot,
                "n_vehicles": n_vehicles_today,
            }
            if forecast_informed:
                policy_kwargs.update(
                    {
                        "future_capacity_pressure": min_ratio,
                        "pressure_k_star": k_star,
                    }
                )

            robust_decision = None
            if self.robust_controller is not None and not forecast_informed:
                shock_state = self.shock_state_builder.build(
                    day_index=day_idx,
                    current_date=self.current_date,
                    visible_orders=visible_open_orders,
                    prev_planned_ids=self.prev_planned_ids,
                    daily_capacity_colli=daily_cap_colli,
                    capacity_ratio_today=ratio,
                    prev_day_planned=self.prev_day_planned,
                    prev_day_vrp_dropped=self.prev_day_vrp_dropped,
                    prev_day_failures=self.prev_day_failures,
                    buffer_order_ids=self.buffer_order_ids,
                    max_trips_per_vehicle=int(
                        self.config.get("max_trips_per_vehicle", 2)
                    ),
                    vehicle_count_today=n_vehicles_today,
                    prev_day_compute_limit=self.prev_day_compute_limit,
                    prev_day_routes=self.prev_day_routes,
                    depot=self.depot,
                )
                robust_decision = self.robust_controller.choose_action(
                    shock_state=shock_state,
                    visible_orders=visible_open_orders,
                    analyzer=analyzer,
                    base_config=self.config,
                    policy=self.policy,
                    policy_kwargs=policy_kwargs,
                )
                policy_kwargs["control_action"] = robust_decision.action

            todays_orders = self.policy.select_orders(**policy_kwargs)

            planned_ids_today = [o["id"] for o in todays_orders]
            current_selected_ids = set(planned_ids_today)

            # -------------------------
            # Compute budget
            # -------------------------
            policy_debug = getattr(self.policy, "last_debug_info", {}) or {}
            env_base_compute = _as_int(os.environ.get("VRP_TIME_LIMIT_SECONDS"), 60)
            base_compute = _as_int(self.config.get("base_compute"), env_base_compute)
            env_high_compute = _as_int(
                os.environ.get("VRP_HIGH_COMPUTE_LIMIT"), base_compute
            )
            high_compute = _as_int(self.config.get("high_compute"), env_high_compute)
            compute_policy = _as_str(
                self.config.get("compute_policy"), "static"
            ).lower()
            mid_compute = _as_optional_int(self.config.get("mid_compute"))
            low_mid_compute = _as_optional_int(self.config.get("low_mid_compute"))
            ratio_thresh_high = _as_optional_float(self.config.get("ratio_thresh_high"))
            ratio_thresh_mid = _as_optional_float(self.config.get("ratio_thresh_mid"))
            ratio_thresh_low_mid = _as_optional_float(
                self.config.get("ratio_thresh_low_mid")
            )

            # -------------------------
            # Learned allocator integration
            # -------------------------
            allocator_action_raw = None
            allocator_action_final = None
            allocator_fallback_reason = None
            allocator_lambda = None
            allocator_model_name = None
            # Historical allocator audit fields are retained for output compatibility.
            allocator_debug = None
            allocator_qhat = {30: 0.0, 60: 0.0, 120: 0.0, 300: 0.0}
            allocator_epsilon = 0.0
            allocator_propensity = 1.0
            allocator_triggered_guards = []
            allocator_exploration = False
            allocator_policy_name = "none"

            # Allocator support is disabled in the retained thesis line.
            use_learned_allocator = False
            if self.config.get("use_learned_allocator", False):
                allocator_fallback_reason = "disabled_in_retained_thesis_line"

            # Build allocator-style feature dict only for backward-compatible audit output.
            allocator_features = {
                "capacity_ratio": float(ratio),
                "visible_open_orders": float(len(visible_open_orders)),
                "mandatory_count": float(policy_debug.get("mandatory_count", 0)),
                "prev_drop_rate": float(
                    self.prev_day_vrp_dropped / self.prev_day_planned
                )
                if self.prev_day_planned and self.prev_day_planned > 0
                else 0.0,
                "prev_failures": float(self._get_prev_failures()),
                "served_colli_lag1": float(self.daily_stats[-1]["served_colli"])
                if self.daily_stats
                else 0.0,
                "vrp_dropped_lag1": float(self.prev_day_vrp_dropped)
                if self.prev_day_vrp_dropped is not None
                else 0.0,
                "failures_lag1": float(self._get_prev_failures()),
                "due_today_count": float(policy_debug.get("due_today_count", 0)),
                "due_soon_count": float(policy_debug.get("due_soon_count", 0)),
                "day_index": float(len(self.daily_stats)),
            }
            if forecast_informed:
                allocator_features.update(
                    {
                        "capacity_pressure": float(min_ratio),
                        "pressure_k_star": float(k_star),
                        "target_load": float(
                            analyzer.target_load_profile.get(d_str, 0.0)
                        ),
                    }
                )

            runtime_mode = "configured"
            runtime_mode_reason = "configured_defaults"
            runtime_mode_selector_enabled = bool(
                self.config.get("runtime_mode_selector_enabled", False)
            )

            # Compute limit decision
            if use_learned_allocator and allocator_action_final is not None:
                # Use learned allocator's decision
                compute_limit = allocator_action_final
                compute_stage = "allocator"
            elif (
                robust_decision is not None
                and robust_decision.action.compute_limit is not None
            ):
                compute_limit = int(robust_decision.action.compute_limit)
                compute_stage = "robust_action"
            else:
                # Fallback to configured rule-based compute policy.
                if use_learned_allocator and allocator_fallback_reason is None:
                    allocator_fallback_reason = "allocator_not_loaded"
                compute_limit, compute_stage = resolve_compute_limit(
                    base_compute=base_compute,
                    high_compute=high_compute,
                    compute_policy=compute_policy,
                    mid_compute=mid_compute,
                    low_mid_compute=low_mid_compute,
                    k_star=k_star,
                    min_ratio=min_ratio,
                    ratio_thresh_high=ratio_thresh_high,
                    ratio_thresh_mid=ratio_thresh_mid,
                    ratio_thresh_low_mid=ratio_thresh_low_mid,
                )

            if runtime_mode_selector_enabled:
                runtime_mode, runtime_mode_reason = resolve_runtime_mode(
                    visible_open_orders=int(len(visible_open_orders)),
                    due_today_count=int(policy_debug.get("due_today_count", 0)),
                    due_soon_count=int(policy_debug.get("due_soon_count", 0)),
                    mandatory_count=int(policy_debug.get("mandatory_count", 0)),
                    capacity_ratio_today=float(ratio),
                    prev_day_vrp_dropped=self.prev_day_vrp_dropped,
                    prev_day_failures=int(self.prev_day_failures or 0),
                    prev_day_warehouse_reason_code=str(
                        self.prev_day_warehouse_reason_code or ""
                    ),
                )
                if runtime_mode == "fixed300":
                    compute_limit = max(int(high_compute), 300)
                    compute_stage = "runtime_mode_fixed300"
                elif runtime_mode == "dyn90":
                    compute_stage = "runtime_mode_dyn90"
                elif runtime_mode == "dyn60":
                    compute_stage = "runtime_mode_dyn60"

            os.environ["VRP_TIME_LIMIT_SECONDS"] = str(compute_limit)

            # churn(target)
            target_churn_stats = self.calculate_suggestion_churn(
                analyzer, visible_open_orders
            )

            # (optional) turnover between consecutive planned sets (not used in summary)
            if self.prev_selected_ids:
                inter2 = len(self.prev_selected_ids & current_selected_ids)
                union2 = len(self.prev_selected_ids | current_selected_ids)
                _ = 1.0 - (inter2 / union2) if union2 > 0 else 0.0

            self.prev_selected_ids = current_selected_ids

            # VRP
            cost = 0.0
            served_colli = 0.0
            delivered_ids_today = []
            failed_today_count = 0
            vrp_dropped = 0
            vrp_wall_seconds = 0.0
            vrp_routes = 0
            vrp_avg_dist = 0.0
            routes: list[JsonDict] = []
            dropped_raw: list[Any] = []
            result: Optional[JsonDict] = None
            solver_status = "not_run"

            if todays_orders and daily_cap_colli > 0:
                daily_data: JsonDict = {
                    "metadata": _as_dict(self.data.get("metadata", {})),
                    "depot": self.depot,
                    "vehicles": adjusted_vehicles,
                    "orders": todays_orders,
                }
                daily_vrp_config = dict(vrp_config)
                if runtime_mode_selector_enabled:
                    if runtime_mode == "fixed300":
                        daily_vrp_config["solver_chunk_seconds"] = int(compute_limit)
                        daily_vrp_config["solver_max_no_improve_chunks"] = 0
                        daily_vrp_config["solver_continue_improvement_ratio"] = 1.0
                        daily_vrp_config["solver_enable_incumbent_continuation"] = False
                        daily_vrp_config["solver_enable_prev_day_route_seed"] = False
                    elif runtime_mode == "dyn90":
                        daily_vrp_config["solver_chunk_seconds"] = 90
                        daily_vrp_config["solver_max_no_improve_chunks"] = 1
                        daily_vrp_config["solver_continue_improvement_ratio"] = 0.0025
                        daily_vrp_config["solver_enable_incumbent_continuation"] = True
                        daily_vrp_config["solver_enable_prev_day_route_seed"] = False
                    elif runtime_mode == "dyn60":
                        daily_vrp_config["solver_chunk_seconds"] = 60
                        daily_vrp_config["solver_max_no_improve_chunks"] = 1
                        daily_vrp_config["solver_continue_improvement_ratio"] = 0.0025
                        daily_vrp_config["solver_enable_incumbent_continuation"] = True
                        daily_vrp_config["solver_enable_prev_day_route_seed"] = False
                initial_routes_by_vehicle = []
                if bool(daily_vrp_config.get("solver_enable_prev_day_route_seed", False)):
                    initial_routes_by_vehicle = _project_prev_day_route_seed(
                        self.prev_day_route_summaries, todays_orders
                    )
                    if sum(len(route) for route in initial_routes_by_vehicle) < 5:
                        initial_routes_by_vehicle = []
                if initial_routes_by_vehicle:
                    daily_vrp_config["initial_routes_by_vehicle"] = initial_routes_by_vehicle
                solver = RoutingGlsSolver(daily_data, d_str, config=daily_vrp_config)
                wall_start = time.perf_counter()
                raw_result = solver.solve()
                vrp_wall_seconds = time.perf_counter() - wall_start
                result = _as_result_dict(raw_result)

                if result is not None:
                    solver_status = _as_str(result.get("solver_status"), "success")
                    routes = _as_list_of_dicts(result.get("routes", []))
                    vrp_routes = len(routes)
                    dists = [
                        _as_float(route.get("distance", 0.0), 0.0) for route in routes
                    ]
                    vrp_avg_dist = (sum(dists) / len(dists)) if dists else 0.0

                    dropped_candidate = result.get(
                        "dropped_indices",
                        result.get("dropped", result.get("dropped_orders", [])),
                    )
                    dropped_raw = _as_list(dropped_candidate)
                    vrp_dropped = len(dropped_raw)

                    # delivered ids
                    delivered_set = set()
                    for route in routes:
                        stops = _as_list(route.get("stops", []))
                        for stop in stops:
                            oid = _normalize_stop_to_order_id(
                                stop, todays_orders, self.orders_map
                            )
                            if oid is not None:
                                delivered_set.add(oid)
                    delivered_ids_today = list(delivered_set)

                    # VRP-dropped orders: mark as failure ONLY if dropped on its deadline day
                    if dropped_raw:
                        for d in dropped_raw:
                            oid = _normalize_dropped_to_order_id(
                                d, todays_orders, self.orders_map
                            )
                            if oid is None:
                                continue
                            o = self.orders_map.get(oid)
                            if not o:
                                continue
                            fds = o.get("feasible_dates") or []
                            if fds and fds[-1] == d_str:
                                self._log_failure(
                                    oid, d_str, reason="vrp_dropped_on_deadline"
                                )
                                failed_today_count += 1

                    # commit deliveries + cost
                    self.completed_order_ids.update(delivered_ids_today)
                    cost = float(result.get("cost", 0.0))
                    for oid in delivered_ids_today:
                        served_colli += float(self.orders_map[oid]["demand"]["colli"])
                    self.total_horizon_cost += cost
                else:
                    solver_status = "no_solution"

            # Post-VRP deadline sweep: any order whose deadline is today and not delivered is a fail.
            # We disambiguate:
            #   - if it was planned today -> VRP-level unserved (routing/time-window/solver)
            #   - if it was NOT planned today -> policy-level rejection/unserved
            delivered_set_today = set(delivered_ids_today)
            planned_set_today = set(planned_ids_today)
            for o in visible_open_orders:
                oid = o["id"]
                if oid in delivered_set_today:
                    continue
                if oid in self.failed_order_ids:
                    continue
                fds = o.get("feasible_dates") or []
                if fds and fds[-1] == d_str:
                    if oid in planned_set_today:
                        self._log_failure(oid, d_str, reason="vrp_unserved_on_deadline")
                    else:
                        self._log_failure(
                            oid, d_str, reason="policy_rejected_or_unserved"
                        )
                    failed_today_count += 1

            # carryover pool (planned but not delivered)
            carry_today = set(planned_ids_today) - delivered_set_today

            self.vrp_audit_traces.append(
                {
                    "date": d_str,
                    "day_idx": int(day_idx),
                    "visible_open_order_ids": [
                        o.get("id") for o in visible_open_orders
                    ],
                    "planned_order_ids": list(planned_ids_today),
                    "delivered_order_ids": list(delivered_ids_today),
                    "vrp_dropped_order_ids": list(dropped_raw)
                    if (todays_orders and daily_cap_colli > 0 and result)
                    else [],
                    "routes": routes
                    if (todays_orders and daily_cap_colli > 0 and result)
                    else [],
                    "solver_attempt_records": result.get("solver_attempt_records", [])
                    if (todays_orders and daily_cap_colli > 0 and result)
                    else [],
                    "solver_warm_start_source": result.get("solver_warm_start_source", "")
                    if (todays_orders and daily_cap_colli > 0 and result)
                    else "",
                    "solver_chunk_count": int(result.get("solver_chunk_count", 0))
                    if (todays_orders and daily_cap_colli > 0 and result)
                    else 0,
                    "warehouse_reason": result.get("warehouse_reason", {})
                    if (todays_orders and daily_cap_colli > 0 and result)
                    else {},
                    "capacity_ratio": float(ratio),
                    "daily_capacity_colli": float(daily_cap_colli),
                }
            )

            planned_prev_count = len(carry_prev)
            planned_curr_count = len(carry_today)
            planned_intersection = len(carry_prev & carry_today)
            planned_union = len(carry_prev | carry_today)

            plan_churn_raw = (
                1.0 - (planned_intersection / planned_union)
                if planned_union > 0
                else 0.0
            )
            plan_churn_effective = plan_churn_raw

            # Update carryover pool for next day
            self.prev_planned_ids = carry_today
            buffered_ids_today = set(
                getattr(self.policy, "last_trace", {}).get("buffered_ids", [])
            )
            self.buffer_order_ids = {
                oid
                for oid in buffered_ids_today
                if oid not in delivered_set_today and oid not in self.failed_order_ids
            }
            next_age = {}
            for oid in carry_today:
                next_age[str(oid)] = int(self.carryover_age.get(str(oid), 0)) + 1
            self.carryover_age = next_age

            target_load_value = analyzer.get_day_target_load(d_str)
            logged_target_load = (
                float(target_load_value)
                if pd.notna(target_load_value)
                else float("nan")
            )
            logged_target_churn = (
                float(target_churn_stats["rate"])
                if getattr(analyzer, "uses_oracle_targets", True)
                else 0.0
            )
            logged_target_churn_common = (
                int(target_churn_stats["intersection"])
                if getattr(analyzer, "uses_oracle_targets", True)
                else 0
            )
            logged_target_churn_count = (
                int(target_churn_stats["count"])
                if getattr(analyzer, "uses_oracle_targets", True)
                else 0
            )
            logged_capacity_pressure = (
                float(min_ratio) if forecast_informed else float("nan")
            )
            logged_pressure_k_star = (
                int(k_star) if forecast_informed and k_star is not None else -1
            )

            self.daily_stats.append(
                {
                    "date": d_str,
                    "cost": cost,
                    "failures": int(failed_today_count),
                    "served_colli": float(served_colli),
                    "target_load": logged_target_load,
                    "target_churn": logged_target_churn,
                    "target_churn_common": logged_target_churn_common,
                    "target_churn_count": logged_target_churn_count,
                    "plan_churn_raw": float(plan_churn_raw),
                    "plan_churn_effective": float(plan_churn_effective),
                    "planned_prev_count": int(planned_prev_count),
                    "planned_curr_count": int(planned_curr_count),
                    "planned_intersection": int(planned_intersection),
                    "planned_union": int(planned_union),
                    "mode_status": policy_debug.get("mode_status", "unknown"),
                    "kept_count": int(policy_debug.get("kept_count", 0)),
                    "frozen_count": int(policy_debug.get("frozen_count", 0)),
                    "mandatory_count": int(policy_debug.get("mandatory_count", 0)),
                    "capacity_pressure": logged_capacity_pressure,
                    "pressure_k_star": logged_pressure_k_star,
                    "capacity_ratio": float(ratio),
                    "capacity": float(daily_cap_colli),
                    "visible_open_orders": int(len(visible_open_orders)),
                    "visible_due_today_count": int(
                        policy_debug.get("due_today_count", 0)
                    ),
                    "visible_due_soon_count": int(
                        policy_debug.get("due_soon_count", 0)
                    ),
                    "planned_today": int(len(planned_ids_today)),
                    "delivered_today": int(len(delivered_ids_today)),
                    "vrp_routes": int(vrp_routes),
                    "vrp_avg_dist": float(vrp_avg_dist),
                    "vrp_dropped": int(vrp_dropped),
                    "vrp_wall_seconds": float(vrp_wall_seconds),
                    "vrp_trip_count": int(result.get("trip_count", 0))
                    if result is not None
                    else 0,
                    "vrp_trip1_attempt_count": int(result.get("trip1_attempt_count", 0))
                    if result is not None
                    else 0,
                    "vrp_trip2plus_attempt_count": int(result.get("trip2plus_attempt_count", 0))
                    if result is not None
                    else 0,
                    "vrp_trip1_wall_seconds": float(result.get("trip1_wall_seconds", 0.0))
                    if result is not None
                    else 0.0,
                    "vrp_trip2plus_wall_seconds": float(result.get("trip2plus_wall_seconds", 0.0))
                    if result is not None
                    else 0.0,
                    "vrp_warehouse_retry_count_total": int(result.get("warehouse_retry_count_total", 0))
                    if result is not None
                    else 0,
                    "vrp_warehouse_filter_solve_count_total": int(result.get("warehouse_filter_solve_count_total", 0))
                    if result is not None
                    else 0,
                    "vrp_trip2_gate_passed": int(result.get("trip2_gate_passed", False))
                    if result is not None
                    else 0,
                    "vrp_trip2_skip_reason": str(result.get("trip2_skip_reason", ""))
                    if result is not None
                    else "",
                    "vrp_remaining_orders_after_trip1": int(result.get("remaining_orders_after_trip1", 0))
                    if result is not None
                    else 0,
                    "vrp_remaining_colli_after_trip1": float(result.get("remaining_colli_after_trip1", 0.0))
                    if result is not None
                    else 0.0,
                    "vrp_trip1_delivery_ratio": float(result.get("trip1_delivery_ratio", 0.0))
                    if result is not None
                    else 0.0,
                    "solver_status": str(solver_status),
                    "solver_budget_planned_seconds": int(compute_limit),
                    "solver_budget_used_seconds": int(result.get("solver_budget_used_seconds", 0))
                    if result is not None
                    else 0,
                    "solver_chunk_count": int(result.get("solver_chunk_count", 0))
                    if result is not None
                    else 0,
                    "solver_no_improve_chunks": int(result.get("solver_no_improve_chunks", 0))
                    if result is not None
                    else 0,
                    "solver_last_improvement_ratio": float(result.get("solver_last_improvement_ratio", 0.0))
                    if result is not None
                    else 0.0,
                    "solver_warm_start_used": int(bool(result.get("solver_warm_start_used", False)))
                    if result is not None
                    else 0,
                    "solver_warm_start_source": str(result.get("solver_warm_start_source", ""))
                    if result is not None
                    else "",
                    "solver_initial_seed_orders": int(result.get("solver_initial_seed_orders", 0))
                    if result is not None
                    else 0,
                    "solver_initial_seed_vehicles": int(result.get("solver_initial_seed_vehicles", 0))
                    if result is not None
                    else 0,
                    "warehouse_reason_code": str((result.get("warehouse_reason", {}) or {}).get("reason", ""))
                    if result is not None
                    else "",
                    "warehouse_reason_bucket": int((result.get("warehouse_reason", {}) or {}).get("bucket", -1))
                    if result is not None and (result.get("warehouse_reason", {}) or {}).get("bucket") is not None
                    else -1,
                    "runtime_mode_selector_enabled": int(runtime_mode_selector_enabled),
                    "runtime_mode_selected": str(runtime_mode),
                    "runtime_mode_reason": str(runtime_mode_reason),
                    "compute_limit_budget_seconds": int(compute_limit),
                    "compute_limit_seconds": int(
                        compute_limit
                    ),  # Actual limit used today
                    "compute_base_seconds": int(
                        base_compute
                    ),  # Config base (for audit)
                    "compute_high_seconds": int(
                        high_compute
                    ),  # Config high (for audit)
                    "compute_stage": str(compute_stage),
                    # Allocator fields
                    "allocator_enabled": int(use_learned_allocator),
                    "allocator_action_raw": int(allocator_action_raw)
                    if allocator_action_raw is not None
                    else -1,
                    "allocator_action_final": int(allocator_action_final)
                    if allocator_action_final is not None
                    else -1,
                    "allocator_lambda": float(allocator_lambda)
                    if allocator_lambda is not None
                    else -1.0,
                    "allocator_model": str(allocator_model_name)
                    if allocator_model_name
                    else "",
                    "allocator_fallback_reason": str(allocator_fallback_reason)
                    if allocator_fallback_reason
                    else "",
                    # Additional allocator audit fields
                    "allocator_policy": str(allocator_policy_name),
                    "allocator_epsilon": float(allocator_epsilon),
                    "allocator_propensity": float(allocator_propensity),
                    "allocator_exploration": int(allocator_exploration),
                    "allocator_qhat_30": float(allocator_qhat.get(30, 0.0)),
                    "allocator_qhat_60": float(allocator_qhat.get(60, 0.0)),
                    "allocator_qhat_120": float(allocator_qhat.get(120, 0.0)),
                    "allocator_qhat_300": float(allocator_qhat.get(300, 0.0)),
                    "allocator_triggered_guards": ",".join(allocator_triggered_guards)
                    if allocator_triggered_guards
                    else "",
                    "robust_controller_enabled": int(
                        self.robust_controller is not None
                    ),
                    "robust_action_name": robust_decision.action.name
                    if robust_decision is not None
                    else "",
                    "robust_action_score": float(robust_decision.action_score)
                    if robust_decision is not None
                    else 0.0,
                    "robust_candidate_count": int(robust_decision.candidate_count)
                    if robust_decision is not None
                    else 0,
                    "robust_evaluated_candidate_count": int(
                        robust_decision.evaluated_candidate_count
                    )
                    if robust_decision is not None
                    else 0,
                    "robust_candidate_limit": int(robust_decision.candidate_limit)
                    if robust_decision is not None
                    else 0,
                    "robust_belief_persistence": float(
                        robust_decision.belief_shock_persistence
                    )
                    if robust_decision is not None
                    else 0.0,
                    "robust_belief_backlog_growth": float(
                        robust_decision.belief_backlog_growth
                    )
                    if robust_decision is not None
                    else 0.0,
                    "robust_belief_recovery": float(
                        robust_decision.belief_recovery_strength
                    )
                    if robust_decision is not None
                    else 0.0,
                    "robust_scenario_loss_mean": float(
                        robust_decision.scenario_loss_mean
                    )
                    if robust_decision is not None
                    else 0.0,
                    "robust_scenario_loss_cvar": float(
                        robust_decision.scenario_loss_cvar
                    )
                    if robust_decision is not None
                    else 0.0,
                    "exec_effective_capacity_colli": float(
                        getattr(robust_decision.action, "effective_capacity_colli", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "exec_effective_capacity_ratio": float(
                        (
                            getattr(
                                robust_decision.action, "effective_capacity_colli", 0.0
                            )
                            or 0.0
                        )
                        / max(1.0, float(daily_cap_colli))
                    )
                    if robust_decision is not None
                    else 0.0,
                    "exec_effective_stop_budget": int(
                        getattr(robust_decision.action, "effective_stop_budget", 0) or 0
                    )
                    if robust_decision is not None
                    else 0,
                    "exec_route_feasibility_score": float(
                        getattr(robust_decision.action, "route_feasibility_score", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "exec_fragmentation_risk": float(
                        getattr(robust_decision.action, "fragmentation_risk", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "exec_trip_penalty": float(
                        getattr(robust_decision.action, "trip_penalty", 0.0) or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "exec_dispersion_penalty": float(
                        getattr(robust_decision.action, "dispersion_penalty", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "exec_drop_penalty": float(
                        getattr(robust_decision.action, "drop_penalty", 0.0) or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "exec_route_dispersion_index": float(
                        getattr(shock_state, "route_dispersion_index", 0.0)
                    )
                    if robust_decision is not None
                    else 0.0,
                    "v6_stage": (
                        "v6a"
                        if robust_decision is not None
                        and str(self.config.get("robust_controller_version", ""))
                        .lower()
                        .startswith("v6a")
                        else "v6b"
                        if robust_decision is not None
                        and str(
                            self.config.get("robust_controller_version", "")
                        ).lower()
                        in {
                            "v6b_value_rerank",
                            "v6b1_value_rerank",
                            "v6b2_guarded_value_rerank",
                            "v6b3_diversified_value_rerank",
                        }
                        else ""
                    ),
                    "v6_frontier_id": str(
                        getattr(robust_decision.action, "frontier_id", "")
                    )
                    if robust_decision is not None
                    else "",
                    "v6_risk_budget_epsilon": float(
                        getattr(robust_decision.action, "risk_budget_epsilon", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "v6_commitment_capacity_colli": float(
                        (
                            getattr(
                                robust_decision.action, "effective_capacity_colli", 0.0
                            )
                            or 0.0
                        )
                        - (
                            getattr(
                                robust_decision.action, "buffer_capacity_colli", 0.0
                            )
                            or 0.0
                        )
                    )
                    if robust_decision is not None
                    else 0.0,
                    "v6_buffer_capacity_colli": float(
                        getattr(robust_decision.action, "buffer_capacity_colli", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "v6_commit_count": int(
                        len(
                            getattr(robust_decision.action, "committed_order_ids", ())
                            or ()
                        )
                    )
                    if robust_decision is not None
                    else 0,
                    "v6_buffer_count": int(
                        len(
                            getattr(robust_decision.action, "buffered_order_ids", ())
                            or ()
                        )
                    )
                    if robust_decision is not None
                    else 0,
                    "v6_defer_count": int(
                        len(
                            getattr(robust_decision.action, "deferred_order_ids", ())
                            or ()
                        )
                    )
                    if robust_decision is not None
                    else 0,
                    "v6_p2_threshold": float(
                        getattr(robust_decision.action, "p2_criticality_threshold", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "v6_release_ratio": float(
                        getattr(robust_decision.action, "p3_release_ratio", 0.0) or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "v6_pred_failure_mean": float(robust_decision.failure_risk_mean)
                    if robust_decision is not None
                    else 0.0,
                    "v6_pred_failure_cvar": float(robust_decision.failure_risk_cvar)
                    if robust_decision is not None
                    else 0.0,
                    "v6_pred_penalized_cost_proxy": float(
                        robust_decision.scenario_loss_mean
                    )
                    if robust_decision is not None
                    else 0.0,
                    "v6_selected_colli": float(
                        sum(
                            float(o.get("demand", {}).get("colli", 0.0))
                            for o in todays_orders
                        )
                    ),
                    "v6_selected_due_today_colli": float(
                        sum(
                            float(
                                self.orders_map[o["id"]]
                                .get("demand", {})
                                .get("colli", 0.0)
                            )
                            for o in todays_orders
                            if (
                                self.orders_map[o["id"]].get("feasible_dates") or [None]
                            )[-1]
                            == d_str
                        )
                    )
                    if todays_orders
                    else 0.0,
                    "v6_selected_due_soon_colli": float(
                        sum(
                            float(
                                self.orders_map[o["id"]]
                                .get("demand", {})
                                .get("colli", 0.0)
                            )
                            for o in todays_orders
                            if 0
                            < _days_until(
                                (
                                    self.orders_map[o["id"]].get("feasible_dates")
                                    or [None]
                                )[-1],
                                self.current_date,
                            )
                            <= 2
                        )
                    )
                    if todays_orders
                    else 0.0,
                    "v6_compute_limit_source": "fixed_external"
                    if str(self.config.get("robust_controller_version", ""))
                    .lower()
                    .startswith("v6a")
                    else "",
                    "v6_compute_limit_used": int(compute_limit)
                    if str(self.config.get("robust_controller_version", ""))
                    .lower()
                    .startswith("v6a")
                    else -1,
                    "v6b_value_hat": float(
                        getattr(robust_decision.action, "value_to_go_estimate", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "v6b_value_model_kind": str(
                        getattr(robust_decision.action, "value_model_kind", "")
                    )
                    if robust_decision is not None
                    else "",
                    "value_action_reserve_ratio": float(
                        getattr(robust_decision.action, "reserve_capacity_ratio", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_flex_ratio": float(
                        getattr(robust_decision.action, "flex_commitment_ratio", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_release_ratio": float(
                        getattr(robust_decision.action, "p3_release_ratio", 0.0) or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_compute_limit": float(
                        getattr(robust_decision.action, "compute_limit", compute_limit)
                        or compute_limit
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_effective_capacity_ratio": float(
                        (
                            getattr(
                                robust_decision.action, "effective_capacity_colli", 0.0
                            )
                            or 0.0
                        )
                        / max(1.0, float(daily_cap_colli))
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_fragmentation_risk": float(
                        getattr(robust_decision.action, "fragmentation_risk", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_trip_penalty": float(
                        getattr(robust_decision.action, "trip_penalty", 0.0) or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_route_feasibility_score": float(
                        getattr(robust_decision.action, "route_feasibility_score", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_commit_count": int(
                        len(
                            getattr(robust_decision.action, "committed_order_ids", ())
                            or ()
                        )
                    )
                    if robust_decision is not None
                    else 0,
                    "value_action_buffer_count": int(
                        len(
                            getattr(robust_decision.action, "buffered_order_ids", ())
                            or ()
                        )
                    )
                    if robust_decision is not None
                    else 0,
                    "value_action_defer_count": int(
                        len(
                            getattr(robust_decision.action, "deferred_order_ids", ())
                            or ()
                        )
                    )
                    if robust_decision is not None
                    else 0,
                    "value_action_candidate_profile": str(
                        getattr(robust_decision.action, "candidate_profile", "")
                    )
                    if robust_decision is not None
                    else "",
                    "value_action_candidate_profile_penalty": float(
                        getattr(
                            robust_decision.action, "candidate_profile_penalty", 0.0
                        )
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_guardrail_penalty": float(
                        getattr(robust_decision.action, "guardrail_penalty", 0.0) or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_guardrail_flags": str(
                        getattr(robust_decision.action, "guardrail_flags", "")
                    )
                    if robust_decision is not None
                    else "",
                    "value_action_execution_guard_level": float(
                        getattr(robust_decision.action, "execution_guard_level", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_execution_penalty_spread": float(
                        getattr(robust_decision.action, "execution_penalty_spread", 0.0)
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_hard_stop_reservation_ratio": float(
                        getattr(
                            robust_decision.action, "hard_stop_reservation_ratio", 0.0
                        )
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                    "value_action_hard_capacity_reservation_ratio": float(
                        getattr(
                            robust_decision.action,
                            "hard_capacity_reservation_ratio",
                            0.0,
                        )
                        or 0.0
                    )
                    if robust_decision is not None
                    else 0.0,
                }
            )

            # store previous-day VRP outcomes for next-day policy heuristics
            self.prev_day_planned = int(len(planned_ids_today))
            self.prev_day_vrp_dropped = int(vrp_dropped)
            self.prev_day_failures = int(failed_today_count)  # For allocator features
            self.prev_day_compute_limit = int(compute_limit)
            self.prev_day_routes = int(vrp_routes)
            self.prev_day_route_summaries = copy.deepcopy(routes)
            self.prev_day_warehouse_reason_code = str(
                (result.get("warehouse_reason", {}) or {}).get("reason", "")
            ) if result is not None else ""

            # -------------------------
            # Feedback Loop: Call policy.on_day_end to update memory
            # -------------------------
            if hasattr(self.policy, "on_day_end"):
                day_stats_for_policy = {
                    "planned": int(len(planned_ids_today)),
                    "vrp_dropped": int(vrp_dropped),
                    "failures": int(failed_today_count),
                }
                self.policy.on_day_end(day_stats_for_policy)

            # -------------------------
            # Update bandit allocator with reward.
            # -------------------------
            # Learned allocator updates are disabled in the retained thesis line.
            # Allocator audit fields are still carried in the daily stats for
            # backward-compatible result schemas, but no online update is applied.

            self._last_completed_date = d_str
            self._persist_progress(partial_status="running")
            self.current_date += timedelta(days=1)

        return self.calculate_metrics()

    # ---------------------------------
    # metrics + outputs
    # ---------------------------------
    def calculate_metrics(self):
        if not self.daily_stats:
            self._write_progress_marker(partial_status="completed")
            return {}

        df = pd.DataFrame(self.daily_stats)
        df_fail = self._failed_orders_frame()
        summary_final = self._build_summary(
            horizon_end=self.end_date, partial_status="completed"
        )

        for output_dir in self._output_dirs():
            df.to_csv(os.path.join(output_dir, "daily_stats.csv"), index=False)
            df_fail.to_csv(os.path.join(output_dir, "failed_orders.csv"), index=False)
            with open(
                os.path.join(output_dir, "summary_final.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(summary_final, f, indent=2)

        self._write_progress_marker(partial_status="completed")
        return summary_final


def resolve_compute_limit(
    *,
    base_compute: int,
    high_compute: int,
    compute_policy: str = "static",
    mid_compute: Optional[int] = None,
    low_mid_compute: Optional[int] = None,
    k_star: Optional[int] = None,
    min_ratio: Optional[float] = None,
    ratio_thresh_high: Optional[float] = None,
    ratio_thresh_mid: Optional[float] = None,
    ratio_thresh_low_mid: Optional[float] = None,
) -> tuple[int, str]:
    """
    Resolve today's solver budget.
    """
    if compute_policy == "kstar_rule":
        k = int(k_star) if k_star is not None else 999
        m = float(min_ratio) if min_ratio is not None else 1.0
        middle = int(
            mid_compute
            if mid_compute is not None
            else (high_compute + base_compute) // 2
        )
        lower_middle = int(
            low_mid_compute if low_mid_compute is not None else base_compute * 2
        )
        if k <= 1 or m <= 0.55:
            return int(high_compute), "high"
        if k <= 3 or m <= 0.65:
            return int(middle), "mid"
        if k <= 6 or m <= 0.75:
            return int(lower_middle), "low_mid"
        return int(base_compute), "base"

    if compute_policy == "ratio_rule":
        m = float(min_ratio) if min_ratio is not None else 1.0
        middle = int(mid_compute if mid_compute is not None else 180)
        lower_middle = int(low_mid_compute if low_mid_compute is not None else 120)
        t_h = float(ratio_thresh_high if ratio_thresh_high is not None else 0.55)
        t_m = float(ratio_thresh_mid if ratio_thresh_mid is not None else 0.65)
        t_l = float(ratio_thresh_low_mid if ratio_thresh_low_mid is not None else 0.75)
        if m <= t_h:
            return int(high_compute), "high"
        if m <= t_m:
            return int(middle), "mid"
        if m <= t_l:
            return int(lower_middle), "low_mid"
        return int(base_compute), "base"

    if compute_policy == "kstar_binary":
        k = int(k_star) if k_star is not None else 999
        if k <= 2:
            return int(high_compute), "high"
        return int(base_compute), "base"
    return int(base_compute), "base"


# ==========================================
# Convenience wrapper for master_runner.py
# ==========================================
def run_rolling_horizon(config):
    """
    Wrapper function for master_runner.py compatibility.

    Args:
        config: dict with keys:
            - capacity_ratio: float
            - total_days: int
            - seed: int
            - crunch_start: int (optional)
            - crunch_end: int (optional)
            - mode: str (optional) - 'greedy' or 'proactive' (default: 'proactive')

    Returns:
        dict: summary_final from RollingHorizonIntegrated.run()
    """
    from .policies import GreedyPolicy, ProactivePolicy

    # Load data
    config_map = _as_dict(config)
    data_path_value = config_map.get(
        "data_path",
        config_map.get("data_file", "data/processed/multiday_benchmark_herlev.json"),
    )
    data_path = Path(
        _as_str(data_path_value, "data/processed/multiday_benchmark_herlev.json")
    )
    if not data_path.is_absolute():
        data_path = Path(_REPO_ROOT) / data_path
    with open(data_path, "r") as f:
        data = json.load(f)

    # Pass experiment knobs through to the policy layer so HPC overrides can
    # exercise the proactive/crisis logic without patching code again.
    total_days = _as_int(config_map.get("total_days"), 12)
    crunch_start = _as_optional_int(config_map.get("crunch_start"))
    crunch_end = _as_optional_int(config_map.get("crunch_end"))

    strategy_config = dict(config_map)
    strategy_config.setdefault(
        "capacity_ratio", _as_float(config_map.get("capacity_ratio"), 1.0)
    )
    strategy_config.setdefault("total_days", total_days)
    strategy_config.setdefault(
        "base_compute", _as_int(config_map.get("base_compute"), 60)
    )
    strategy_config.setdefault(
        "high_compute", _as_int(config_map.get("high_compute"), 60)
    )
    strategy_config.setdefault(
        "compute_policy", _as_str(config_map.get("compute_policy"), "static")
    )

    # Add crunch period if specified
    if crunch_start is not None and crunch_end is not None:
        strategy_config["crunch_start"] = crunch_start
        strategy_config["crunch_end"] = crunch_end

    # Build capacity_profile from crunch parameters
    # Supports both single window (crunch_start/end) and multi-window (crunch_windows)
    capacity_profile: JsonDict = {}
    raw_crunch_windows = _as_list(config_map.get("crunch_windows", []))
    crunch_windows: list[tuple[int, int]] = []
    for window in raw_crunch_windows:
        if (
            isinstance(window, (list, tuple))
            and len(window) == 2
            and _as_optional_int(window[0]) is not None
            and _as_optional_int(window[1]) is not None
        ):
            crunch_windows.append((_as_int(window[0], 0), _as_int(window[1], 0)))
    crunch_ratio = _as_float(config_map.get("capacity_ratio"), 1.0)

    # Normalize: convert single window to list format for unified handling
    if not crunch_windows and crunch_start is not None and crunch_end is not None:
        crunch_windows = [(crunch_start, crunch_end)]

    for day_idx in range(total_days):
        if crunch_windows:
            # Check if day_idx falls within any crunch window
            in_crunch = any(start <= day_idx <= end for start, end in crunch_windows)
            capacity_profile[str(day_idx)] = crunch_ratio if in_crunch else 1.0
        else:
            # No crunch period: use capacity_ratio for all days (BAU scenario)
            capacity_profile[str(day_idx)] = crunch_ratio

    # Inject capacity_profile into data metadata
    metadata = _as_dict(data.get("metadata", {}))
    metadata["capacity_profile"] = capacity_profile
    data["metadata"] = metadata

    # Determine policy mode (greedy vs proactive)
    mode = _as_str(config_map.get("mode"), "proactive").lower()

    # Create policy based on mode
    if mode == "greedy":
        strategy_config["mode"] = "greedy"
        policy = GreedyPolicy(config=strategy_config)
        strategy_name = "Greedy"
    else:
        strategy_config["mode"] = "proactive_quota"
        policy = ProactivePolicy(config=strategy_config)
        strategy_name = "Proactive"

    # Create simulator
    simulator = RollingHorizonIntegrated(
        data_source=data,
        strategy_config=strategy_config,
        seed=_as_int(config_map.get("seed"), 42),
        verbose=bool(config_map.get("verbose", False)),
        run_context={
            "scenario": _as_str(config_map.get("scenario"), "DEFAULT"),
            "strategy": strategy_name,
        },
        base_dir=config_map.get("base_dir"),
        results_dir=_as_str(config_map.get("results_dir"), "data/results"),
        run_id=config_map.get("run_id"),
    )

    # Override end_date if total_days is specified
    if "total_days" in config and config["total_days"] is not None:
        from datetime import timedelta

        simulator.end_date = simulator.start_date + timedelta(
            days=config["total_days"] - 1
        )

    # Set policy
    simulator.policy = policy

    # Run simulation
    summary = simulator.run_simulation()

    # Return both summary and daily_stats for master_runner compatibility
    return {
        "daily_stats": simulator.daily_stats,
        "vrp_audit_traces": simulator.vrp_audit_traces,
        "summary": summary,
        **summary,  # Include all summary fields at top level for backward compatibility
    }
